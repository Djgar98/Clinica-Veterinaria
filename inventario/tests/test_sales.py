from django.test import TestCase
from django.contrib.auth import get_user_model
from inventario.models import Producto, Venta, SaleItem, VentaAudit

User = get_user_model()


class SaleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass')
        from inventario.models import Categoria
        cat = Categoria.objects.create(name='General')
        self.prod = Producto.objects.create(nombre='P1', stock_inicial=10, precio='5.00', categoria=cat)

    def test_apply_stock_decrements(self):
        venta = Venta.objects.create(created_by=self.user, updated_by=self.user)
        item = SaleItem.objects.create(venta=venta, producto=self.prod, cantidad=3, precio_unitario='5.00')
        # recalc and apply
        venta.apply_stock_changes()
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_inicial, 7)
        venta.refresh_from_db()
        self.assertTrue(venta.stock_committed)

    def test_insufficient_stock_raises(self):
        venta = Venta.objects.create(created_by=self.user, updated_by=self.user)
        SaleItem.objects.create(venta=venta, producto=self.prod, cantidad=20, precio_unitario='5.00')
        with self.assertRaises(ValueError):
            venta.apply_stock_changes()
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_inicial, 10)

    def test_apply_only_once(self):
        venta = Venta.objects.create(created_by=self.user, updated_by=self.user)
        SaleItem.objects.create(venta=venta, producto=self.prod, cantidad=2, precio_unitario='5.00')
        venta.apply_stock_changes()
        venta.apply_stock_changes()  # second call should be no-op
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock_inicial, 8)