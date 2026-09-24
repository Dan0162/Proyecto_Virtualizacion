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
        <label>
          Cliente
          <select v-model="cliente_id" required>
            <option value="" disabled>Selecciona un cliente…</option>
            <option v-for="c in clientes" :key="c.id" :value="c.id">
              {{ c.nombre }} ({{ c.email }})
            </option>
          </select>
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
        <template v-else-if="pedidos.length">
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Carné</th>
                <th>Productos</th>
                <th>Total</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in pedidos"
                :key="p.id"
                @click="verDetalles(p)"
                class="clickable-row"
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
                <td class="mono">
                  {{ formatMoneda(totalPedido(p)) }}
                </td>
                <td>
                  {{ p.estado }}
                </td>
                <td>
                  <template v-if="p.estado === 'pendiente'">
                    <button class="primary" style="margin-right: 0.5rem; padding: 0.2rem 0.5rem; font-size: 0.8rem;" @click.stop="cambiarEstadoPedido(p.id, 'confirmado')">✓</button>
                    <button class="danger" style="padding: 0.2rem 0.5rem; font-size: 0.8rem;" @click.stop="cambiarEstadoPedido(p.id, 'cancelado')">✕</button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
          <p class="mono total-general">
            Total general: {{ formatMoneda(totalGeneral) }}
          </p>
        </template>
        <div
          v-else
          class="empty-state"
        >
          Todavía no hay pedidos registrados.
        </div>
      </div>
    </div>
    
    <!-- Modal de Detalles del Pedido -->
    <div v-if="mostrarModal" class="modal-overlay" @click="cerrarModal">
      <div class="modal-content" @click.stop>
        <header class="modal-header">
          <h2>Detalles del Pedido #{{ pedidoSeleccionado.id }}</h2>
          <button class="close-button" @click="cerrarModal">✕</button>
        </header>
        <div class="modal-body">
          <p><strong>Cliente:</strong> {{ getNombreCliente(pedidoSeleccionado.cliente_id) }}</p>
          <p><strong>Carné_responsable:</strong> {{ pedidoSeleccionado.carne_integrante }}</p>
          <p><strong>Estado:</strong> {{ pedidoSeleccionado.estado }}</p>
          <table>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Precio Unitario</th>
                <th>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in pedidoSeleccionado.detalles" :key="d.id">
                <td>{{ getNombreProducto(d.sku) }} ({{ d.sku }})</td>
                <td>{{ d.cantidad }}</td>
                <td class="mono">{{ formatMoneda(d.precio_unitario_q) }}</td>
                <td class="mono">{{ formatMoneda(d.cantidad * d.precio_unitario_q) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="mono total-general">
            Total: {{ formatMoneda(totalPedido(pedidoSeleccionado)) }}
          </p>
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
  clientesApi,
} from "../api";

const productos = ref([]);
const stock = ref([]);
const clientes = ref([]);
const cliente_id = ref("");
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

const pedidoSeleccionado = ref(null);
const mostrarModal = ref(false);

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

const totalGeneral = computed(() =>
  pedidos.value.reduce((suma, p) => suma + totalPedido(p), 0)
);

function verDetalles(pedido) {
  pedidoSeleccionado.value = pedido;
  mostrarModal.value = true;
}

function cerrarModal() {
  mostrarModal.value = false;
  pedidoSeleccionado.value = null;
}

function getNombreProducto(sku) {
  const producto = productos.value.find((p) => p.sku === sku);
  return producto ? producto.nombre : sku;
}

function getNombreCliente(id) {
  const cliente = clientes.value.find((c) => c.id === id);
  return cliente ? cliente.nombre : `ID: ${id}`;
}

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

function totalPedido(pedido) {
  if (!pedido.detalles?.length) return 0;
  return pedido.detalles.reduce(
    (suma, d) => suma + d.cantidad * (d.precio_unitario_q ?? 0),
    0
  );
}

function formatMoneda(valor) {
  return new Intl.NumberFormat("es-GT", {
    style: "currency",
    currency: "GTQ",
  }).format(valor);
}

async function cargarProductos() {
  try {
    const [catalogo, existencias, listaClientes] =
      await Promise.all([
        catalogoApi.listar(),
        inventarioApi.listar(),
        clientesApi.listar(),
      ]);
    productos.value = catalogo;
    stock.value = existencias;
    clientes.value = listaClientes;
  } catch (e) {
    errorPedido.value =
      `No se pudo cargar los datos iniciales: ${e.message}`;
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
  if (!cliente_id.value) {
    errorPedido.value = "Debes seleccionar un cliente.";
    return;
  }
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
      cliente_id: cliente_id.value,
      carne_integrante: carne.value,
      detalles,
    });
    mensajeExito.value =
      "Pedido creado correctamente.";
    carne.value = "";
    cliente_id.value = "";
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

async function cambiarEstadoPedido(id, nuevoEstado) {
  try {
    await pedidosApi.actualizarEstado(id, nuevoEstado);
    await cargarHistorial();
    // Also reload products in case stock changed
    await cargarProductos();
  } catch (e) {
    errorHistorial.value = `No se pudo actualizar el estado: ${e.message}`;
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
  grid-template-columns: 1fr;
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
.total-general {
  margin-top: 0.75rem;
  font-weight: 600;
}
/* @media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
} */

.clickable-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.clickable-row:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: var(--color-surface);
  padding: 1.5rem;
  border-radius: var(--radius);
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.close-button {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  padding: 0.5rem;
}
.close-button:hover {
  border-color: transparent;
  color: var(--color-accent);
}
.modal-body p {
  margin: 0.25rem 0;
}
.modal-body table {
  margin-top: 1rem;
}
</style>
