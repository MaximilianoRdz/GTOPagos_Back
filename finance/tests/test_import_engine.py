import pandas as pd
from datetime import date
from django.test import TestCase
from finance.services.import_engine import ImportEngine

class TestImportEngine(TestCase):
    def test_msi_detection_standard(self):
        description = "COMPRA EN LIVERPOOL 03/12 MSI"
        is_inst, current, total = ImportEngine.detect_msi(description)
        self.assertTrue(is_inst)
        self.assertEqual(current, 3)
        self.assertEqual(total, 12)

    def test_msi_detection_starting(self):
        description = "COMPRA EN LIVERPOOL 12 MSI"
        is_inst, current, total = ImportEngine.detect_msi(description)
        self.assertTrue(is_inst)
        self.assertEqual(current, 1)
        self.assertEqual(total, 12)

    def test_msi_detection_with_de(self):
        description = "PAGO 2 DE 6 MESES SIN INTERESES"
        is_inst, current, total = ImportEngine.detect_msi(description)
        self.assertTrue(is_inst)
        self.assertEqual(current, 2)
        self.assertEqual(total, 6)
        
    def test_msi_detection_starting_meses(self):
        description = "A 18 MESES SIN INTERESES"
        is_inst, current, total = ImportEngine.detect_msi(description)
        self.assertTrue(is_inst)
        self.assertEqual(current, 1)
        self.assertEqual(total, 18)

    def test_clean_amount(self):
        self.assertEqual(ImportEngine.clean_amount("$1,234.56"), 1234.56)
        self.assertEqual(ImportEngine.clean_amount(" 1,000.00 "), 1000.0)
        self.assertEqual(ImportEngine.clean_amount("invalid"), 0.0)
        self.assertEqual(ImportEngine.clean_amount("$-500.00"), -500.0)

    # Note: detect_category tests would require DB mocking or fixtures,
    # so we focus on the pure logic parts that don't need DB access for now.
