"""
Seed realistic demo data: buildings, units, occupants, occupancies and a
history of payments (with generated invoice PDFs).

    python manage.py seed_demo            # creates data + admin user
    python manage.py seed_demo --flush    # wipe existing data first
"""

import random
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.properties.models import Building, Flat, Level, Occupant, Occupancy
from apps.payments.models import Payment
from apps.payments.services import create_invoice_for_payment
from apps.payments.utils import due_date_for

BENGALI_FIRST = ["Rahim", "Karim", "Anik", "Tanvir", "Sabbir", "Nusrat", "Farhana",
                 "Mehedi", "Rakibul", "Shahriar", "Tania", "Mamun", "Jewel", "Arif",
                 "Sadia", "Imran", "Hasan", "Rumana", "Faisal", "Nahar"]
BENGALI_LAST = ["Uddin", "Ahmed", "Islam", "Hossain", "Rahman", "Khan", "Chowdhury",
                "Akter", "Sultana", "Mia", "Talukdar", "Bhuiyan", "Sheikh"]
SHOPS = ["Green Grocers", "Niharika Tailors", "Rana Pharmacy", "Cafe Nirmal"]

BUILDINGS = [
    ("B-01", "Shapla Residence", "House 12, Road 5, Dhanmondi, Dhaka"),
    ("B-02", "Korotoya Tower", "Plot 44, Pragati Sarani, Gulshan 2, Dhaka"),
    ("B-03", "Titas Cottage", "Block C, Bashundhara R/A, Dhaka"),
]


class Command(BaseCommand):
    help = "Seed demo data for RentFlow."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete existing business data first.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["flush"]:
            Payment.objects.all().delete()
            Occupancy.objects.all().delete()
            Flat.objects.all().delete()
            Level.objects.all().delete()
            Building.objects.all().delete()
            Occupant.objects.all().delete()
            self.stdout.write("Existing data flushed.")

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "admin@rentflow.app", "admin1234")
            self.stdout.write(self.style.SUCCESS(
                "Admin user created -> username: admin   password: admin1234"))

        random.seed(42)
        today = timezone.localdate()

        occupants = []
        used_names = set()
        for _ in range(18):
            name = f"{random.choice(BENGALI_FIRST)} {random.choice(BENGALI_LAST)}"
            if name in used_names:
                continue
            used_names.add(name)
            phone = f"017{random.randint(10, 99)}-{random.randint(100000, 999999)}"
            occ = Occupant.objects.create(
                name=name,
                email=f"{name.split()[0].lower()}{random.randint(1, 99)}@gmail.com",
                phone=phone,
                nid_number=f"199{random.randint(1000000000, 9999999999)}",
                occupation=random.choice(["Service", "Business", "Student", "Doctor"]),
                present_address="Dhaka, Bangladesh",
                emergency_contact_phone=f"018{random.randint(10, 99)}-{random.randint(100000, 999999)}",
            )
            occupants.append(occ)

        occ_index = 0
        for b_no, b_name, addr in BUILDINGS:
            building = Building.objects.create(building_no=b_no, name=b_name, address=addr)
            for lvl in range(0, 6):
                Level.objects.create(
                    building=building, level_number=lvl,
                    name="Ground Floor" if lvl == 0 else f"Level {lvl}")

            units = []
            if b_no == "B-03":  # cottages
                for i in range(1, 5):
                    units.append(Flat.objects.create(
                        building=building, flat_no=f"C-{i}",
                        flat_type=Flat.FlatType.COTTAGE, size_sqft=random.choice([900, 1100, 1250]),
                        amenities="Parking, Garden", default_rent=Decimal(random.choice([18000, 22000]))))
            else:
                for lvl in range(0, 6):
                    for letter in ("A", "B"):
                        f = Flat.objects.create(
                            building=building, level=building.levels.get(level_number=lvl),
                            flat_no=f"{letter}-{lvl + 1}", flat_type=Flat.FlatType.FLAT,
                            size_sqft=random.choice([750, 950, 1100, 1250]),
                            amenities="Lift, Generator, Parking",
                            default_rent=Decimal(random.choice([12000, 14000, 16000, 18000, 22000])))
                        units.append(f)
                # Ground-floor shops
                for i in range(1, 3):
                    units.append(Flat.objects.create(
                        building=building, level=building.levels.first(),
                        flat_no=f"S-{i}", flat_type=Flat.FlatType.SHOP,
                        size_sqft=random.choice([300, 450]),
                        amenities="Front road, Signage",
                        default_rent=Decimal(random.choice([25000, 30000]))))

            # Occupy ~75% of units
            random.shuffle(units)
            for unit in units[: int(len(units) * 0.75)]:
                if occ_index >= len(occupants):
                    break
                person = occupants[occ_index]
                occ_index += 1
                start = date(today.year - random.randint(0, 1),
                             random.randint(1, max(today.month, 1)), 1)
                if start > today:
                    start = date(today.year, 1, 1)
                rent = unit.default_rent
                occupancy = Occupancy.objects.create(
                    flat=unit, occupant=person, start_date=start,
                    rent_amount=rent, advance_amount=rent,
                    agreement_reference=f"AGR-{b_no}-{unit.flat_no}")

                # Payment history: pay most months, leave a few unpaid for demos
                y, m = start.year, start.month
                months = []
                while (y, m) <= (today.year, today.month):
                    months.append((y, m))
                    m += 1
                    if m > 12:
                        m, y = 1, y + 1
                # Keep the last 0-3 months unpaid depending on tenant
                skip_last = random.choice([0, 0, 1, 1, 2, 3])
                payable = months[: len(months) - skip_last] if skip_last else months
                for (py, pm) in payable:
                    method = random.choice([Payment.Method.CASH, Payment.Method.BANK,
                                            Payment.Method.BKASH])
                    details = {}
                    if method == Payment.Method.CASH:
                        details = {"received_by": "M. Karim (Manager)",
                                   "received_date": due_date_for(py, pm).isoformat()}
                    elif method == Payment.Method.BANK:
                        details = {"sender_bank": random.choice(
                                       ["City Bank Ltd.", "BRAC Bank Ltd.", "Eastern Bank Ltd."]),
                                   "receiver_bank": "City Bank Ltd.",
                                   "txn_ref": f"TXN{random.randint(10**9, 10**10 - 1)}",
                                   "transfer_date": due_date_for(py, pm).isoformat(),
                                   "cheque_no": ""}
                    else:
                        details = {"txn_id": f"{random.randint(10**9, 10**10 - 1)}",
                                   "sender_number": person.phone,
                                   "txn_datetime": due_date_for(py, pm).isoformat() + " 10:30"}
                    p = Payment(
                        occupancy=occupancy, rent_year=py, rent_month=pm, amount=rent,
                        payment_date=due_date_for(py, pm), due_date=due_date_for(py, pm),
                        method=method, status=Payment.Status.PAID, details=details)
                    p.save()
                    create_invoice_for_payment(p)

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {Building.objects.count()} buildings, "
            f"{Flat.objects.count()} units, {Occupant.objects.count()} occupants, "
            f"{Payment.objects.count()} payments / invoices."))
