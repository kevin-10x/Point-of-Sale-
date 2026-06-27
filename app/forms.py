from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterShopForm(FlaskForm):
    shop_name = StringField("Shop Name", validators=[DataRequired(), Length(max=200)])
    shop_phone = StringField("Shop Phone", validators=[Optional(), Length(max=20)])
    shop_email = StringField("Shop Email", validators=[Optional(), Email(), Length(max=100)])
    shop_address = StringField("Address", validators=[Optional(), Length(max=255)])
    username = StringField("Owner Username", validators=[DataRequired(), Length(max=100)])
    email = StringField("Owner Email", validators=[Optional(), Email(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])


class ProductForm(FlaskForm):
    name = StringField("Product Name", validators=[DataRequired(), Length(max=200)])
    barcode = StringField("Barcode", validators=[Optional(), Length(max=100)])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    buying_price = FloatField(
        "Buying Price (KSh)",
        validators=[DataRequired(), NumberRange(min=0)],
    )
    selling_price = FloatField(
        "Selling Price (KSh)",
        validators=[DataRequired(), NumberRange(min=0)],
    )
    stock_quantity = IntegerField(
        "Stock Quantity",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    low_stock_threshold = IntegerField(
        "Low Stock Alert",
        validators=[DataRequired(), NumberRange(min=0)],
        default=5,
    )


class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=100)])


class CustomerForm(FlaskForm):
    name = StringField("Customer Name", validators=[DataRequired(), Length(max=200)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=100)])


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    role = SelectField(
        "Role",
        choices=[("cashier", "Cashier"), ("manager", "Manager"), ("owner", "Owner")],
        validators=[DataRequired()],
    )


class BranchForm(FlaskForm):
    name = StringField("Branch Name", validators=[DataRequired(), Length(max=100)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
