from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.properties.models import Building, Flat, Occupant, Occupancy
from apps.payments.models import Invoice, Payment
from apps.payments.services import create_invoice_for_payment
from apps.payments.utils import (
    due_date_for, due_periods, next_invoice_number, outstanding_totals,
    shift_month,
)


class MonthLogicTests(TestCase):
    def test_shift_month(self):
        self.assertEqual(shift_month(2026, 1, -1), (2025, 12))
        self.assertEqual(shift_month(2026, 12, 1), (2027, 1))
        self.assertEqual(shift_month(2026, 6, 2), (2026, 8))

    def test_due_date(self):
        self.assertEqual(due_date_for(2026, 9), date(2026, 9, 10))

    def test_due_periods_detects_overdue(self):
        b = Building.objects.create(building_no="B1", name="B")
        f = Flat.objects.create(building=b, flat_no="1", default_rent=Decimal("10000"))
        o = Occupant.objects.create(name="Test", phone="1", nid_number="99")
        occ = Occupancy.objects.create(flat=f, occupant=o, start_date=date(2026, 6, 1),
                                       rent_amount=Decimal("10000"))
        periods = due_periods(occ, today=date(2026, 9, 7))
        labels = [p["label"] for p in periods]
        self.assertEqual(labels, ["June 2026", "July 2026", "August 2026", "September 2026"])
        self.assertTrue(any(p["status"] == "overdue" for p in periods))

    def test_paid_months_excluded(self):
        b = Building.objects.create(building_no="B2", name="B")
        f = Flat.objects.create(building=b, flat_no="2", default_rent=Decimal("10000"))
        o = Occupant.objects.create(name="Test2", phone="2", nid_number="88")
        occ = Occupancy.objects.create(flat=f, occupant=o, start_date=date(2026, 8, 1),
                                       rent_amount=Decimal("10000"))
        Payment.objects.create(occupancy=occ, rent_year=2026, rent_month=8,
                               amount=Decimal("10000"), payment_date=date(2026, 8, 5),
                               due_date=due_date_for(2026, 8),
                               method=Payment.Method.CASH, status=Payment.Status.PAID,
                               details={"received_by": "X"})
        periods = due_periods(occ, today=date(2026, 9, 7))
        self.assertNotIn("August 2026", [p["label"] for p in periods])
        self.assertIn("September 2026", [p["label"] for p in periods])

    def test_invoice_number_and_pdf(self):
        n1 = next_invoice_number()
        self.assertTrue(n1.startswith("INV-"))
        b = Building.objects.create(building_no="B3", name="B")
        f = Flat.objects.create(building=b, flat_no="3", default_rent=Decimal("5000"))
        o = Occupant.objects.create(name="T3", phone="3")
        occ = Occupancy.objects.create(flat=f, occupant=o, start_date=date(2026, 9, 1),
                                       rent_amount=Decimal("5000"))
        p = Payment.objects.create(occupancy=occ, rent_year=2026, rent_month=9,
                                   amount=Decimal("5000"), payment_date=date(2026, 9, 5),
                                   due_date=due_date_for(2026, 9), method=Payment.Method.CASH,
                                   status=Payment.Status.PAID, details={})
        inv, _buf = create_invoice_for_payment(p)
        self.assertTrue(inv.invoice_number.startswith("INV-2026-09-"))
        self.assertTrue(inv.pdf.read().startswith(b"%PDF"))

    def test_outstanding_totals(self):
        b = Building.objects.create(building_no="B4", name="B")
        f = Flat.objects.create(building=b, flat_no="4", default_rent=Decimal("10000"))
        o = Occupant.objects.create(name="T4", phone="4")
        Occupancy.objects.create(flat=f, occupant=o, start_date=date(2026, 8, 1),
                                 rent_amount=Decimal("10000"))
        totals = outstanding_totals(today=date(2026, 9, 7))
        self.assertGreater(totals["outstanding"], 0)
        self.assertGreaterEqual(totals["outstanding"], totals["overdue"])


class PortalViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "a@a.com", "admin1234")
        self.client.login(username="admin", password="admin1234")
        self.b = Building.objects.create(building_no="BX", name="Bldg")
        self.f = Flat.objects.create(building=self.b, flat_no="9", default_rent=Decimal("12000"))
        self.o = Occupant.objects.create(name="Portal User", phone="017", email="u@x.com",
                                         nid_number="123")
        self.occ = Occupancy.objects.create(flat=self.f, occupant=self.o,
                                            start_date=date(2026, 9, 1),
                                            rent_amount=Decimal("12000"))

    def test_flat_info_returns_occupant(self):
        resp = self.client.get(f"/payments/api/flat/{self.f.id}/info/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["occupied"])
        self.assertEqual(data["occupant"]["name"], "Portal User")

    def test_verify_rejects_bad_amount(self):
        resp = self.client.post("/payments/api/verify/",
                                {"occupancy_id": self.occ.id,
                                 "periods": [{"year": 2026, "month": 9}],
                                 "amount": 100, "method": "cash",
                                 "details": {"received_by": "X"}},
                                content_type="application/json")
        self.assertFalse(resp.json()["ok"])

    def test_generate_creates_payment_and_pdf(self):
        resp = self.client.post("/payments/api/generate/",
                                {"occupancy_id": self.occ.id,
                                 "periods": [{"year": 2026, "month": 9}],
                                 "method": "cash",
                                 "details": {"received_by": "Karim",
                                             "received_date": "2026-09-07"},
                                 "payment_date": "2026-09-07",
                                 "send_email": False},
                                content_type="application/json")
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        pdf = self.client.get(data["invoices"][0]["pdf_url"])
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
