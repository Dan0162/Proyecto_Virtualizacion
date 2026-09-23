<template>
  <div>
    <header class="view-header">
      <div>
        <h1>Inventario</h1>
        <p class="subtitle">
          Productos, categorías y existencias
        </p>
      </div>

      <button class="primary" @click="abrirNuevo">
        + Nuevo producto
      </button>
    </header>

    <div v-if="cargando" class="empty-state">
      Cargando inventario…
    </div>

    <div v-else-if="error" class="error-state">
      {{ error }}
    </div>

    <table v-else-if="productos.length">
      <thead>
        <tr>
          <th>SKU</th>
          <th>Nombre</th>
          <th>Categoría</th>
          <th>Precio</th>
          <th>Stock</th>
          <th>Stock mínimo</th>
          <th></th>
        </tr>
      </thead>

      <tbody>
        <tr
          v-for="p in productos"
          :key="p.sku"
          :class="{ 'stock-bajo': p.stock <= p.stock_minimo }"
        >
          <td class="mono">{{ p.sku }}</td>
          <td>{{ p.nombre }}</td>
          <td>{{ p.categoria }}</td>
          <td class="mono">{{ formatQ(p.precio_q) }}</td>
          <td class="mono">{{ p.stock }}</td>
          <td class="mono">{{ p.stock_minimo }}</td>

          <td class="row-actions">
            <button @click="abrirEdicion(p)">
              Editar
            </button>

            <button
              class="danger"
              @click="eliminar(p)"
            >
              Eliminar
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty-state">
      Todavía no hay productos registrados.
      Crea el primero con "Nuevo producto".
    </div>

    <div
      v-if="mostrarForm"
      class="modal-backdrop"
      @click.self="cerrarForm"
    >
      <form
        class="modal card"
        @submit.prevent="guardar"
      >
        <h2>
          {{ editando ? "Editar producto" : "Nuevo producto" }}
        </h2>

        <label>
          SKU
          <input
            v-model.trim="form.sku"
            required
            :disabled="!!editando"
            maxlength="30"
          />
        </label>

        <label>
          Nombre
          <input
            v-model.trim="form.nombre"
            required
            maxlength="120"
          />
        </label>

        <label>
          Categoría
          <input
            v-model.trim="form.categoria"
            required
            maxlength="60"
          />
        </label>

        <label>
          Precio (Q)
          <input
            v-model.number="form.precio_q"
            type="number"
            min="0"
            step="0.01"
            required
          />
        </label>

        <label>
          Stock
          <input
            v-model.number="form.cantidad"
            type="number"
            min="0"
            step="1"
            required
          />
        </label>

        <label>
          Stock mínimo
          <input
            v-model.number="form.stock_minimo"
            type="number"
            min="0"
            step="1"
            required
          />
        </label>

        <p
          v-if="errorForm"
          class="error-state"
        >
          {{ errorForm }}
        </p>

        <div class="modal-actions">
          <button
            type="button"
            @click="cerrarForm"
          >
            Cancelar
          </button>

          <button
            type="submit"
            class="primary"
            :disabled="guardando"
          >
            {{ guardando ? "Guardando…" : "Guardar" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import {
  catalogoApi,
  inventarioApi,
} from "../api";

const productos = ref([]);

const cargando = ref(true);
const error = ref("");

const mostrarForm = ref(false);
const editando = ref(null);
const guardando = ref(false);
const errorForm = ref("");

const form = reactive({
  sku: "",
  nombre: "",
  categoria: "",
  precio_q: 0,
  cantidad: 0,
  stock_minimo: 0,
});

function formatQ(valor) {
  return new Intl.NumberFormat("es-GT", {
    style: "currency",
    currency: "GTQ",
  }).format(valor ?? 0);
}

async function cargar() {
  cargando.value = true;
  error.value = "";

  try {
    const [catalogo, stock] = await Promise.all([
      catalogoApi.listar(),
      inventarioApi.listar(),
    ]);

    const stockPorSku = new Map(
      stock.map((item) => [
        item.sku,
        item,
      ])
    );

    productos.value = catalogo.map((producto) => {
      const existencia = stockPorSku.get(producto.sku);

      return {
        ...producto,
        stock: existencia?.cantidad ?? 0,
        stock_minimo: existencia?.stock_minimo ?? 0,
      };
    });
  } catch (e) {
    error.value =
      `No se pudo cargar el inventario: ${e.message}`;
  } finally {
    cargando.value = false;
  }
}

function abrirNuevo() {
  editando.value = null;

  Object.assign(form, {
    sku: "",
    nombre: "",
    categoria: "",
    precio_q: 0,
    cantidad: 0,
    stock_minimo: 0,
  });

  errorForm.value = "";
  mostrarForm.value = true;
}

function abrirEdicion(producto) {
  editando.value = producto;

  Object.assign(form, {
    sku: producto.sku,
    nombre: producto.nombre,
    categoria: producto.categoria,
    precio_q: producto.precio_q,
    cantidad: producto.stock,
    stock_minimo: producto.stock_minimo,
  });

  errorForm.value = "";
  mostrarForm.value = true;
}

function cerrarForm() {
  mostrarForm.value = false;
}

async function guardar() {
  guardando.value = true;
  errorForm.value = "";

  try {
    if (editando.value) {
      const sku = editando.value.sku;

      await catalogoApi.actualizar(sku, {
        nombre: form.nombre,
        categoria: form.categoria,
        precio_q: form.precio_q,
      });

      await inventarioApi.actualizar(sku, {
        cantidad: form.cantidad,
        stock_minimo: form.stock_minimo,
      });
    } else {
      await catalogoApi.crear({
        sku: form.sku,
        nombre: form.nombre,
        categoria: form.categoria,
        precio_q: form.precio_q,
      });

      try {
        await inventarioApi.crear({
          sku: form.sku,
          cantidad: form.cantidad,
          stock_minimo: form.stock_minimo,
        });
      } catch (e) {
        try {
          await catalogoApi.eliminar(form.sku);
        } catch {
          // Se conserva el error original.
        }

        throw e;
      }
    }

    mostrarForm.value = false;
    await cargar();
  } catch (e) {
    errorForm.value = e.message;
  } finally {
    guardando.value = false;
  }
}

async function eliminar(producto) {
  const confirmado = confirm(
    `¿Eliminar "${producto.nombre}"? Esta acción no se puede deshacer.`
  );

  if (!confirmado) {
    return;
  }

  try {
    await inventarioApi.eliminar(producto.sku);
    await catalogoApi.eliminar(producto.sku);

    await cargar();
  } catch (e) {
    error.value =
      No se pudo eliminar: ${e.message};
  }
}

onMounted(cargar);
</script>

<style scoped>
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.subtitle {
  color: var(--color-ink-muted);
  margin: 0;
}

.stock-bajo td {
  background: rgba(184, 69, 47, 0.06);
}

.row-actions {
  display: flex;
  gap: 0.4rem;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(32, 38, 31, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal {
  width: 100%;
  max-width: 380px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.modal label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: var(--color-ink-muted);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>
