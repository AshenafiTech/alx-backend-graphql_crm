import re
from datetime import datetime
import graphene
from graphene_django import DjangoObjectType
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import Customer, Product, Order

# --- Types ---
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer

class ProductType(DjangoObjectType):
    class Meta:
        model = Product

class OrderType(DjangoObjectType):
    class Meta:
        model = Order

# --- Mutations ---
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        # Email uniqueness
        if Customer.objects.filter(email=email).exists():
            return CreateCustomer(success=False, message="Email already exists.")
        # Phone validation
        if phone:
            phone_regex = re.compile(r"^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$")
            if not phone_regex.match(phone):
                return CreateCustomer(success=False, message="Invalid phone format.")
        customer = Customer(name=name, email=email, phone=phone)
        customer.save()
        return CreateCustomer(customer=customer, success=True, message="Customer created successfully.")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(
            graphene.NonNull(
                graphene.InputObjectType(
                    "CustomerInput",
                    name=graphene.String(required=True),
                    email=graphene.String(required=True),
                    phone=graphene.String()
                )
            )
        )

    created_customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        created = []
        errors = []
        with transaction.atomic():
            for idx, data in enumerate(customers):
                try:
                    if Customer.objects.filter(email=data.email).exists():
                        errors.append(f"Row {idx+1}: Email '{data.email}' already exists.")
                        continue
                    if data.phone:
                        phone_regex = re.compile(r"^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$")
                        if not phone_regex.match(data.phone):
                            errors.append(f"Row {idx+1}: Invalid phone format.")
                            continue
                    customer = Customer(name=data.name, email=data.email, phone=data.phone)
                    customer.save()
                    created.append(customer)
                except Exception as e:
                    errors.append(f"Row {idx+1}: {str(e)}")
        return BulkCreateCustomers(created_customers=created, errors=errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(default_value=0)

    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, price, stock=0):
        if price <= 0:
            return CreateProduct(success=False, message="Price must be positive.")
        if stock < 0:
            return CreateProduct(success=False, message="Stock cannot be negative.")
        product = Product(name=name, price=price, stock=stock)
        product.save()
        return CreateProduct(product=product, success=True, message="Product created successfully.")

class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, customer_id, product_ids, order_date=None):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except ObjectDoesNotExist:
            return CreateOrder(success=False, message="Invalid customer ID.")
        if not product_ids:
            return CreateOrder(success=False, message="At least one product must be selected.")
        products = []
        total_amount = 0
        for pid in product_ids:
            try:
                product = Product.objects.get(pk=pid)
                products.append(product)
                total_amount += product.price
            except ObjectDoesNotExist:
                return CreateOrder(success=False, message=f"Invalid product ID: {pid}")
        order = Order(customer=customer, order_date=order_date or datetime.now(), total_amount=total_amount)
        order.save()
        order.products.set(products)
        return CreateOrder(order=order, success=True, message="Order created successfully.")

# --- Root Mutation ---
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()