import pandas as pd
from datetime import datetime
from finance.models import CategoryKeyword, Category, FinancialRecord, FinancialRecordType
from django.db.models import Q
import numpy as np

class ImportEngine:
    DATE_ALIASES = ['fecha', 'date', 'fecha de operacion', 'fecha operacion', 'dia', 'día']
    DESC_ALIASES = ['concepto', 'descripcion', 'descripción', 'descripcin', 'description', 'detalle', 'movimiento', 'referencia', 'beneficiario', 'nombre', 'comercio', 'transaccion', 'transacción', 'transaccin', 'motivo', 'observaciones', 'concepto / referencia']
    AMOUNT_ALIASES = ['monto', 'amount', 'importe', 'cantidad']
    EXPENSE_ALIASES = ['cargo', 'retiro']
    INCOME_ALIASES = ['abono', 'deposito', 'depósito']
    IGNORED_KEYWORDS = [
        'pago para no generar',
        'pago minimo',
        'pago mínimo',
        'saldo actual',
        'saldo anterior',
        'saldo al corte',
        'deuda total',
        'total a pagar',
        'limite de credito',
        'límite de crédito',
        'credito disponible',
        'crédito disponible'
    ]

    @classmethod
    def find_column(cls, df_columns, aliases):
        for col in df_columns:
            col_lower = str(col).lower().strip()
            for alias in aliases:
                # If the column starts with the alias, or contains it exactly (e.g. 'fecha de operacion' starts with 'fecha')
                if col_lower == alias or col_lower.startswith(alias):
                    return col
        return None

    @classmethod
    def clean_amount(cls, val):
        if isinstance(val, pd.Series):
            val = val.iloc[0]
        # Also check for empty series or arrays just in case
        if hasattr(val, 'empty') and val.empty:
            return 0.0
        
        # In pandas, pd.isna can return an array if val is an array-like object.
        # But since we handled Series, val should be a scalar.
        if pd.isna(val):
            return 0.0
            
        if isinstance(val, str):
            val = val.replace('$', '').replace(',', '').strip()
        try:
            return float(val)
        except ValueError:
            return 0.0

    @classmethod
    def detect_category(cls, description, behavior=None):
        if not description:
            return None, 'Sin categoría'
            
        desc_lower = description.lower()
        
        qs = CategoryKeyword.objects.select_related('category', 'category__record_type')
        if behavior:
            qs = qs.filter(category__record_type__behavior=behavior)
            
        keywords = qs.all()
        
        best_match = None
        best_len = 0
        import re
        import difflib
        
        desc_words = desc_lower.replace('/', ' ').replace('-', ' ').split()
        
        for kw in keywords:
            kw_lower = kw.keyword.lower()
            # Priority 1: word boundary match gets a big weight boost
            if re.search(rf'\b{re.escape(kw_lower)}\b', desc_lower):
                match_weight = len(kw_lower) + 100
                if match_weight > best_len:
                    best_match = kw.category
                    best_len = match_weight
            # Priority 2: regular substring match
            elif kw_lower in desc_lower:
                match_weight = len(kw_lower)
                if match_weight > best_len:
                    best_match = kw.category
                    best_len = match_weight
            # Priority 3: Fuzzy matching (errores ortográficos o abreviaturas)
            else:
                for word in desc_words:
                    similarity = difflib.SequenceMatcher(None, kw_lower, word).ratio()
                    if similarity > 0.85:
                        match_weight = len(kw_lower) * similarity
                        if match_weight > best_len:
                            best_match = kw.category
                            best_len = match_weight
                            
        if best_match:
            return best_match.id, best_match.name
        return None, 'Sin categoría'

    @classmethod
    def check_duplicate(cls, user_id, dashboard_id, date, amount, description):
        # We consider it a duplicate if it matches date, exact amount, and same dashboard/user.
        # Description might vary slightly, but we can do an exact or icontains check.
        qs = FinancialRecord.objects.filter(
            user_id=user_id,
            record_date=date,
            amount=abs(amount),
            is_active=True
        ).filter(description__icontains=description[:20])
        
        if dashboard_id:
            qs = qs.filter(dashboard_id=dashboard_id)
            
        return qs.exists()

    @classmethod
    def detect_msi(cls, description):
        import re
        is_installment = False
        current_installment = 0
        total_installments = 0
        msi_match = re.search(r'(\d{1,2})\s*(?:/|DE|de)\s*(\d{1,2})(?:\s*MSI|\s*MESES)?', description, re.IGNORECASE)
        if msi_match:
            c_inst = int(msi_match.group(1))
            t_inst = int(msi_match.group(2))
            if t_inst > 0 and c_inst <= t_inst:
                is_installment = True
                current_installment = c_inst
                total_installments = t_inst
        else:
            msi_start_match = re.search(r'(?:a\s+)?(\d{1,2})\s*(?:msi|m\.s\.i\.|meses\s*sin\s*intereses|meses\s*s/i|meses)', description, re.IGNORECASE)
            if msi_start_match:
                t_inst = int(msi_start_match.group(1))
                if t_inst > 0:
                    is_installment = True
                    current_installment = 1
                    total_installments = t_inst
        return is_installment, current_installment, total_installments

    @classmethod
    def parse_matrix_file(cls, df, user_id, dashboard_id):
        import re
        from datetime import date
        from collections import defaultdict

        months = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        current_year = datetime.today().year
        
        # We will collect entries by column
        # col_name -> list of (date, amount)
        col_entries = defaultdict(list)
        
        for index, row in df.iterrows():
            period_str = str(row.iloc[0]).lower().strip()
            if not period_str or period_str == 'nan' or 'total' in period_str:
                continue
                
            # Parse date
            month_num = 1
            for m_name, m_num in months.items():
                if m_name in period_str:
                    month_num = m_num
                    break
                    
            day = 1
            if '2q' in period_str or '2da' in period_str or 'quincena 2' in period_str:
                day = 15
                
            try:
                record_date = date(current_year, month_num, day)
            except Exception:
                continue
                
            for col_name in df.columns[1:]:
                col_str = str(col_name).strip()
                if not col_str or col_str.lower() == 'total' or 'unnamed' in col_str.lower():
                    continue
                    
                val = row[col_name]
                amount = cls.clean_amount(val)
                if amount <= 0:
                    continue
                    
                col_entries[col_str].append((record_date, amount))

        if not col_entries:
            raise ValueError("No se encontraron las columnas requeridas (Fecha, Descripción) y tampoco se pudo leer como Matriz de Presupuesto Quincenal.")

        parsed_records = []
        row_idx = 0
        
        for col_str, entries in col_entries.items():
            # Sort entries by date
            entries.sort(key=lambda x: x[0])
            
            for (rec_date, amount) in entries:
                description = col_str
                cat_id, cat_name = cls.detect_category(description, 'EXPENSE')
                is_duplicate = cls.check_duplicate(user_id, dashboard_id, rec_date, amount, description)
                
                is_installment, current_installment, total_installments = cls.detect_msi(description)

                parsed_records.append({
                    'row_index': row_idx,
                    'record_date': rec_date.isoformat(),
                    'description': description,
                    'amount': amount,
                    'behavior': 'EXPENSE',
                    'category_id': cat_id,
                    'category_name': cat_name,
                    'is_duplicate': is_duplicate,
                    'selected': True,
                    'is_recurrent': False,
                    'occurrences': 1,
                    'is_installment': is_installment,
                    'current_installment': current_installment,
                    'total_installments': total_installments
                })
                row_idx += 1
            
        return parsed_records

    @classmethod
    def parse_pdf_to_df(cls, file):
        import pdfplumber
        import pandas as pd
        import re
        
        date_pattern = r'^(\d{2}[-/][a-zA-Z]{3,}[-/]\d{2,4}|\d{2}[-/]\d{2}[-/]\d{2,4})'
        
        rows = []
        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                        
                    for line in text.split('\n'):
                        line = line.strip()
                        date_match = re.match(date_pattern, line, re.IGNORECASE)
                        if date_match:
                            date_str = date_match.group(1)
                            remaining = line[len(date_str):].strip()
                            
                            # Remove secondary date if present
                            second_date = re.match(date_pattern, remaining, re.IGNORECASE)
                            if second_date:
                                remaining = remaining[len(second_date.group(1)):].strip()
                                
                            # Find all amounts
                            amounts_found = list(re.finditer(r'([+-])?\s*\$?\s*([\d,]+\.\d{2})', remaining))
                            if not amounts_found:
                                continue
                                
                            # Find the authoritative amount (last one, or one with a sign)
                            signed_amount = None
                            for match in amounts_found:
                                if match.group(1): 
                                    signed_amount = match
                                    break
                                    
                            target_match = signed_amount if signed_amount else amounts_found[-1]
                            sign = target_match.group(1)
                            amount = float(target_match.group(2).replace(',', ''))
                            
                            desc_end_idx = target_match.start()
                            description = remaining[:desc_end_idx].strip()
                            
                            # Append anything after the amount back to the description (like MSI "3 de 12")
                            remainder = remaining[target_match.end():].strip()
                            if remainder:
                                description += " " + remainder
                                
                            # Filter ignored keywords
                            desc_lower = description.lower()
                            if any(kw in desc_lower for kw in cls.IGNORED_KEYWORDS):
                                continue
                                
                            # Determine behavior
                            is_expense = True
                            if sign == '-':
                                is_expense = False # BBVA Abono
                            
                            if is_expense:
                                rows.append({'Fecha': date_str, 'Descripción': description, 'Cargo': amount, 'Abono': 0.0})
                            else:
                                rows.append({'Fecha': date_str, 'Descripción': description, 'Cargo': 0.0, 'Abono': amount})
                                
        except Exception as e:
            raise ValueError(f"Error procesando PDF: {str(e)}")
            
        if not rows:
            raise ValueError("No se encontraron transacciones válidas en el PDF.")
            
        return pd.DataFrame(rows)

    @classmethod
    def parse_file(cls, file, user_id, dashboard_id):
        # Determine file type
        filename = file.name.lower()
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith('.pdf'):
                df = cls.parse_pdf_to_df(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            raise ValueError(f"No se pudo leer el archivo: {str(e)}")

        # Many bank statements have meta-data at the top. We need to find the real header row.
        # We check if the current columns contain a date alias. If not, we search the first 20 rows.
        cols_lower = [str(c).lower().strip() for c in df.columns]
        
        # Helper to check if any alias is in a list of strings
        def has_date_alias(string_list):
            for s in string_list:
                for alias in cls.DATE_ALIASES:
                    if alias == s or s.startswith(alias):
                        return True
            return False

        if not has_date_alias(cols_lower):
            header_idx = -1
            for i, row in df.head(20).iterrows():
                row_vals = [str(x).lower().strip() for x in row.values]
                if has_date_alias(row_vals):
                    header_idx = i + 1 # +1 because read_excel header is 0-indexed relative to data
                    break
            
            if header_idx != -1:
                if filename.endswith('.pdf'):
                    raw_cols = list(df.iloc[header_idx - 1])
                    seen = {}
                    new_cols = []
                    for c in raw_cols:
                        c_str = str(c).strip() if c is not None else ""
                        if c_str in seen:
                            seen[c_str] += 1
                            new_cols.append(f"{c_str}_{seen[c_str]}")
                        else:
                            seen[c_str] = 0
                            new_cols.append(c_str)
                    
                    df.columns = new_cols
                    df = df[header_idx:].reset_index(drop=True)
                else:
                    file.seek(0)
                    if filename.endswith('.csv'):
                        df = pd.read_csv(file, header=header_idx)
                    else:
                        df = pd.read_excel(file, header=header_idx)

        date_col = cls.find_column(df.columns, cls.DATE_ALIASES)
        desc_col = cls.find_column(df.columns, cls.DESC_ALIASES)
        
        amount_col = cls.find_column(df.columns, cls.AMOUNT_ALIASES)
        expense_col = cls.find_column(df.columns, cls.EXPENSE_ALIASES)
        income_col = cls.find_column(df.columns, cls.INCOME_ALIASES)

        if not date_col:
            return cls.parse_matrix_file(df, user_id, dashboard_id)
            
        if not amount_col and not (expense_col and income_col):
            return cls.parse_matrix_file(df, user_id, dashboard_id)

        parsed_records = []
        
        # Iter rows
        for index, row in df.iterrows():
            raw_date = row[date_col]
            if isinstance(raw_date, pd.Series):
                raw_date = raw_date.iloc[0]
                
            if pd.isna(raw_date):
                continue
                
            try:
                if isinstance(raw_date, str):
                    record_date = pd.to_datetime(raw_date, dayfirst=True).date()
                else:
                    record_date = raw_date.date()
            except Exception:
                continue

            desc_val = row[desc_col] if desc_col else "Cargo/Abono sin descripción"
            if isinstance(desc_val, pd.Series):
                desc_val = desc_val.iloc[0]
                
            description = str(desc_val).strip() if not pd.isna(desc_val) else ""
            if not description:
                continue

            # Skip summary/balance rows that shouldn't be imported as transactions
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in cls.IGNORED_KEYWORDS):
                continue

            amount = 0.0
            behavior = 'EXPENSE'

            if amount_col:
                val = cls.clean_amount(row[amount_col])
                if val < 0:
                    behavior = 'EXPENSE'
                    amount = abs(val)
                else:
                    # In some bank statements, positive is expense, in others positive is income.
                    # We will assume positive = expense unless it's explicitly income. 
                    # Actually, if there is only 'amount_col', it's tricky.
                    # Let's assume standard: negative=expense, positive=income.
                    if val > 0:
                        behavior = 'INCOME'
                        amount = val
            else:
                expense_val = cls.clean_amount(row.get(expense_col, 0))
                income_val = cls.clean_amount(row.get(income_col, 0))
                
                if expense_val > 0:
                    amount = expense_val
                    behavior = 'EXPENSE'
                elif income_val > 0:
                    amount = income_val
                    behavior = 'INCOME'
                else:
                    continue # Both 0

            if amount == 0:
                continue

            cat_id, cat_name = cls.detect_category(description, behavior)
            is_duplicate = cls.check_duplicate(user_id, dashboard_id, record_date, amount, description)

            is_installment, current_installment, total_installments = cls.detect_msi(description)

            parsed_records.append({
                'row_index': index,
                'record_date': record_date.isoformat(),
                'description': description,
                'amount': float(amount),
                'behavior': behavior,
                'category_id': cat_id,
                'category_name': cat_name,
                'is_duplicate': is_duplicate,
                'selected': True,
                'is_recurrent': False,
                'occurrences': 1,
                'is_installment': is_installment,
                'current_installment': current_installment,
                'total_installments': total_installments
            })

        return parsed_records
