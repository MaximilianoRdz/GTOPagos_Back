from django.core.management.base import BaseCommand
from finance.models import FinancialRecordType, Category

class Command(BaseCommand):
    help = 'Popula la base de datos con tipos de registros financieros y categorías iniciales'

    def handle(self, *args, **kwargs):
        data = {
            "Percepción": [  # Income equivalent
                "Sueldo",
                "Aguinaldo",
                "Prima Vacacional",
                "Bonos",
                "Tiempo Extra",
                "Vales de Despensa",
                "Fondo de Ahorro (Patrón)",
                "Reembolsos"
            ],
            "Deducción": [  # Expense equivalent
                "ISR",
                "IMSS",
                "Seguro de Vida",
                "Caja de Ahorro",
                "Préstamo Personal",
                "Anticipo de Nómina",
                "Pensión Alimenticia",
                "Crédito Infonavit"
            ]
        }
        
        self.stdout.write("Iniciando carga de datos...")
        
        for type_name, categories in data.items():
            record_type, created = FinancialRecordType.objects.get_or_create(name=type_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Tipo creado: {type_name}'))
            else:
                self.stdout.write(f'Tipo existente: {type_name}')
            
            for cat_name in categories:
                category, cat_created = Category.objects.get_or_create(
                    name=cat_name, 
                    record_type=record_type
                )
                if cat_created:
                    self.stdout.write(self.style.SUCCESS(f'  - Categoría creada: {cat_name}'))
                else:
                    self.stdout.write(f'  - Categoría existente: {cat_name}')
        
        self.stdout.write(self.style.SUCCESS('¡Carga de datos completada exitosamente!'))
