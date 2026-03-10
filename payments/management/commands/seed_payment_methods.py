from django.core.management.base import BaseCommand

from payments.models import PaymentMethod


class Command(BaseCommand):
    help = "Popula la base de datos con métodos de pago iniciales"

    def handle(self, *args, **options):
        methods = [
            {
                "name": "Efectivo",
                "description": "Pago en efectivo",
            },
            {
                "name": "Tarjeta de débito",
                "description": "Pago con tarjeta de débito",
            },
            {
                "name": "Tarjeta de crédito",
                "description": "Pago con tarjeta de crédito",
            },
            {
                "name": "Transferencia bancaria",
                "description": "Transferencia SPEI o similar",
            },
            {
                "name": "Otros",
                "description": "Otros métodos de pago",
            },
        ]

        self.stdout.write("Iniciando carga de métodos de pago...")

        for item in methods:
            obj, created = PaymentMethod.objects.get_or_create(
                name=item["name"],
                defaults={
                    "description": item["description"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Método creado: {obj.name}"))
            else:
                self.stdout.write(f"Método existente: {obj.name}")

        self.stdout.write(self.style.SUCCESS("Carga de métodos de pago completada"))

