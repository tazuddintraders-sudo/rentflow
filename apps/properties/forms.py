from django import forms

from .models import Building, Document, Flat, Level, Occupant, Occupancy


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ["building_no", "name", "address", "photo"]
        widgets = {
            "building_no": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. B-01"}),
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Building name"}),
            "address": forms.Textarea(attrs={"class": "input", "rows": 2}),
            "photo": forms.FileInput(attrs={"class": "input"}),
        }


class LevelForm(forms.ModelForm):
    class Meta:
        model = Level
        fields = ["building", "level_number", "name"]
        widgets = {
            "building": forms.Select(attrs={"class": "input"}),
            "level_number": forms.NumberInput(attrs={"class": "input", "min": 0}),
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Ground Floor"}),
        }


class FlatForm(forms.ModelForm):
    class Meta:
        model = Flat
        fields = ["building", "level", "flat_no", "flat_type", "size_sqft",
                  "amenities", "default_rent", "notes"]
        widgets = {
            "building": forms.Select(attrs={"class": "input"}),
            "level": forms.Select(attrs={"class": "input"}),
            "flat_no": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. A-2"}),
            "flat_type": forms.Select(attrs={"class": "input"}),
            "size_sqft": forms.NumberInput(attrs={"class": "input", "min": 0}),
            "amenities": forms.TextInput(attrs={"class": "input", "placeholder": "Lift, Parking, Generator"}),
            "default_rent": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 2}),
        }


class OccupantForm(forms.ModelForm):
    class Meta:
        model = Occupant
        fields = [
            "name", "email", "phone", "alt_phone", "id_type", "nid_number",
            "occupation", "present_address", "permanent_address",
            "emergency_contact_name", "emergency_contact_phone", "photo", "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "alt_phone": forms.TextInput(attrs={"class": "input"}),
            "id_type": forms.Select(attrs={"class": "input"}),
            "nid_number": forms.TextInput(attrs={"class": "input"}),
            "occupation": forms.TextInput(attrs={"class": "input"}),
            "present_address": forms.Textarea(attrs={"class": "input", "rows": 2}),
            "permanent_address": forms.Textarea(attrs={"class": "input", "rows": 2}),
            "emergency_contact_name": forms.TextInput(attrs={"class": "input"}),
            "emergency_contact_phone": forms.TextInput(attrs={"class": "input"}),
            "photo": forms.FileInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 2}),
        }


class OccupancyForm(forms.ModelForm):
    class Meta:
        model = Occupancy
        fields = ["flat", "occupant", "start_date", "end_date", "rent_amount",
                  "advance_amount", "agreement_reference", "notes"]
        widgets = {
            "flat": forms.Select(attrs={"class": "input"}),
            "occupant": forms.Select(attrs={"class": "input"}),
            "start_date": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "input", "type": "date"}),
            "rent_amount": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "advance_amount": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "agreement_reference": forms.TextInput(attrs={"class": "input"}),
            "notes": forms.Textarea(attrs={"class": "input", "rows": 2}),
        }


class EndOccupancyForm(forms.Form):
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "input", "type": "date"}),
        help_text="The occupant's last day in this flat.",
    )


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["document_type", "title", "file"]
        widgets = {
            "document_type": forms.Select(attrs={"class": "input"}),
            "title": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. NID front page"}),
            "file": forms.FileInput(attrs={"class": "input"}),
        }
