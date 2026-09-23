<template>
  <div>
    <header class="view-header">
      <div>
        <h1>Pedidos</h1>
        <p class="subtitle">
          Registra pedidos de productos disponibles
        </p>
      </div>
    </header>

    <div class="layout">
      <form
        class="card nuevo-pedido"
        @submit.prevent="confirmarPedido"
      >
        <h2>Nuevo pedido</h2>

        <label>
          Carné del integrante
          <input
            v-model.trim="carne"
            placeholder="Ej. 1053223"
            maxlength="15"
            required
          />
        </label>

        <div class="lineas">
          <div
            v-for="(linea, i) in lineas"
            :key="i"
            class="linea"
          >
            <select
              v-model="linea.sku"
              required
            >
              <option
                value=""
                disabled
              >
                Selecciona un producto…
              </option>

              <option
                v-for="p in productosDisponibles"
                :key="p.sku"
                :value="p.sku"
              >
                {{ p.sku }} —
                {{ p.nombre }}
                ({{ p.cantidad }} disp.)
              </option>
            </select>

            <input
              v-model.number="linea.cantidad"
              type="number"
              min="1"
              step="1"
              required
            />

            <button
              type="button"
              class="danger"
              @click="quitarLinea(i)"
              :disabled="lineas.length === 1"
            >
              ✕
            </button>
          </div>
        </div>

        <button
          type="button"
          @click="agregarLinea"
        >
          + Agregar producto
        </button>

        <p
          v-if="errorPedido"
          class="error-state"
        >
          {{ errorPedido }}
        </p>

        <p
          v-if="mensajeExito"
          class="success-state"
        >
          {{ mensajeExito }}
        </p>

        <button
          type="submit"
          class="primary"
          :disabled="enviando"
        >
          {{ enviando ? "Enviando…" : "Crear pedido" }}
        </button>
      </form>

      <div class="historial">
        <h2>Historial</h2>

        <div
          v-if="cargandoHistorial"
          class="empty-state"
        >
          Cargando pedidos…
        </div>

        <div
          v-else-if="errorHistorial"
          class="error-state"
        >
          {{ errorHistorial }}
        </div>

        <table
          v-else-if="pedidos.length"
        >
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Carné</th>
              <th>Productos</th>
              <th>Estado</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="p in pedidos"
              :key="p.id"
            >
              <td class="mono">
                {{ formatFecha(p.creado_en) }}
              </td>

              <td class="mono">
                {{ p.carne_integrante }}
              </td>

              <td>
                {{ p.detalles?.length ?? 0 }}
                producto(s)
              </td>

              <td>
                {{ p.estado }}
              </td>
            </tr>
          </tbody>
        </table>

        <div
          v-else
          class="empty-state"
        >
          Todavía no hay pedidos registrados.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  onMounted,
  ref,
} from "vue";

import {
  catalogoApi,
  inventarioApi,
  pedidosApi,
} from "../api";

const productos = ref([]);
const stock = ref([]);

const carne = ref("");

const lineas = ref([
  {
    sku: "",
    cantidad: 1,
  },
]);

const enviando = ref(false);
const errorPedido = ref("");
const mensajeExito = ref("");

const pedidos = ref([]);
const cargandoHistorial = ref(true);
const errorHistorial = ref("");

const productosDisponibles = computed(() => {
  const stockPorSku = new Map(
    stock.value.map((item) => [
      item.sku,
      item,
    ])
  );

  return productos.value
    .map((producto) => {
      const existencia =
        stockPorSku.get(producto.sku);

      return {
        ...producto,
        cantidad: existencia?.cantidad ?? 0,
      };
    })
    .filter((producto) => producto.cantidad > 0);
});

function agregarLinea() {
  lineas.value.push({
    sku: "",
    cantidad: 1,
  });
}

function quitarLinea(i) {
  lineas.value.splice(i, 1);
}

function formatFecha(fecha) {
  if (!fecha) {
    return "—";
  }

  return new Date(fecha).toLocaleString("es-GT");
}

async function cargarProductos() {
  try {
    const [catalogo, existencias] =
      await Promise.all([
        catalogoApi.listar(),
        inventarioApi.listar(),
      ]);

    productos.value = catalogo;
    stock.value = existencias;
  } catch (e) {
    errorPedido.value =
      `No se pudo cargar los productos: ${e.message}`;
  }
}

async function cargarHistorial() {
  cargandoHistorial.value = true;
  errorHistorial.value = "";

  try {
    pedidos.value = await pedidosApi.listar();
  } catch (e) {
    errorHistorial.value =
      `No se pudo cargar el historial: ${e.message}`;
  } finally {
    cargandoHistorial.value = false;
  }
}

async function confirmarPedido() {
  errorPedido.value = "";
  mensajeExito.value = "";

  if (!carne.value.trim()) {
    errorPedido.value =
      "El carné del integrante es obligatorio.";
    return;
  }

  if (carne.value.length > 15) {
    errorPedido.value =
      "El carné no puede superar 15 caracteres.";
    return;
  }

  const detalles = [];

  for (const linea of lineas.value) {
    if (!linea.sku) {
      continue;
    }

    const producto = productos.value.find(
      (p) => p.sku === linea.sku
    );

    const existencia = stock.value.find(
      (s) => s.sku === linea.sku
    );

    if (!producto) {
      errorPedido.value =
        `No se encontró el producto ${linea.sku}.`;
      return;
    }

    if (!existencia) {
      errorPedido.value =
        `No existe inventario para ${linea.sku}.`;
      return;
    }

    if (
      !Number.isInteger(linea.cantidad) ||
      linea.cantidad <= 0
    ) {
      errorPedido.value =
        "La cantidad debe ser un número entero mayor que cero.";
      return;
    }

    if (linea.cantidad > existencia.cantidad) {
      errorPedido.value =
        `Stock insuficiente para ${producto.nombre}. Disponible: ${existencia.cantidad}.`;
      return;
    }

    detalles.push({
      sku: producto.sku,
      cantidad: linea.cantidad,
      precio_unitario_q: producto.precio_q,
    });
  }

  if (!detalles.length) {
    errorPedido.value =
      "Agrega al menos un producto al pedido.";
    return;
  }

  enviando.value = true;

  try {
    await pedidosApi.crear({
      carne_integrante: carne.value,
      estado: "confirmado",
      detalles,
    });

    mensajeExito.value =
      "Pedido creado correctamente.";

    carne.value = "";

    lineas.value = [
      {
        sku: "",
        cantidad: 1,
      },
    ];

    await Promise.all([
      cargarProductos(),
      cargarHistorial(),
    ]);
  } catch (e) {
    errorPedido.value = e.message;
  } finally {
    enviando.value = false;
  }
}

onMounted(() => {
  cargarProductos();
  cargarHistorial();
});
</script>

<style scoped>
.view-header {
  margin-bottom: 1.5rem;
}

.subtitle {
  color: var(--color-ink-muted);
  margin: 0;
}

.layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 1.5rem;
  align-items: start;
}

.nuevo-pedido {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.nuevo-pedido label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: var(--color-ink-muted);
}

.lineas {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.linea {
  display: grid;
  grid-template-columns: 1fr 70px auto;
  gap: 0.4rem;
}

.success-state {
  color: var(--color-primary);
  margin: 0;
}

.historial {
  min-width: 0;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
