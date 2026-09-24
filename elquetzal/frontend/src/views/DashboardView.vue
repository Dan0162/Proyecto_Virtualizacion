<template>
  <div>
    <header class="view-header">
      <h1>Dashboard</h1>
      <p class="subtitle">Estado general del inventario y pedidos</p>
    </header>
    <div v-if="cargando" class="empty-state">
      Cargando métricas…
    </div>
    <div v-else-if="error" class="error-state">
      {{ error }}
    </div>
    <template v-else>
      <div class="metric-grid">
        <div class="card metric">
          <span class="metric-label">Productos totales</span>
          <span class="metric-value mono">
            {{ resumen.total_productos }}
          </span>
        </div>
        <div class="card metric">
          <span class="metric-label">Valor del inventario</span>
          <span class="metric-value mono">
            {{ formatQ(resumen.valor_total_inventario_q) }}
          </span>
        </div>
        <div class="card metric">
          <span class="metric-label">Pedidos de hoy</span>
          <span class="metric-value mono">
            {{ resumen.pedidos_del_dia }}
          </span>
        </div>
        <div
          class="card metric"
          :class="{ alerta: stockBajo.length }"
        >
          <span class="metric-label">
            Productos con stock bajo
          </span>
          <span class="metric-value mono">
            {{ stockBajo.length }}
          </span>
        </div>
      </div>
      <div
        v-if="stockBajo.length"
        class="card stock-list"
      >
        <h2>Alerta de stock bajo</h2>
        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Nombre</th>
              <th>Categoría</th>
              <th>Stock</th>
              <th>Mínimo</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in stockBajo"
              :key="p.sku"
            >
              <td class="mono">{{ p.sku }}</td>
              <td>{{ p.nombre }}</td>
              <td>{{ p.categoria }}</td>
              <td class="mono">{{ p.cantidad }}</td>
              <td class="mono">{{ p.stock_minimo }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        v-else
        class="card empty-state"
      >
        No hay productos con stock bajo.
      </div>

      <div class="acciones">
        <button
          type="button"
          class="primary"
          :disabled="exportando"
          @click="exportarPdf"
        >
          {{ exportando ? "Generando PDF…" : "Exportar reporte PDF" }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import { reportesApi } from "../api";

const resumen = ref({
  total_productos: 0,
  valor_total_inventario_q: 0,
  pedidos_del_dia: 0,
});
const stockBajo = ref([]);
const cargando = ref(true);
const error = ref("");
const exportando = ref(false);

const alertas = computed(() => stockBajo.value ?? []);

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
    const data = await reportesApi.resumen();
    resumen.value = data.resumen ?? {
      total_productos: 0,
      valor_total_inventario_q: 0,
      pedidos_del_dia: 0,
    };
    stockBajo.value = data.alertas_stock_bajo ?? [];
  } catch (e) {
    error.value = `No se pudo cargar el dashboard: ${e.message}`;
  } finally {
    cargando.value = false;
  }
}

function exportarPdf() {
  exportando.value = true;
  try {
    const doc = new jsPDF();
    const fecha = new Date().toLocaleString("es-GT");

    // Título
    doc.setFontSize(16);
    doc.text("Reporte de Dashboard", 14, 18);
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generado: ${fecha}`, 14, 25);
    doc.setTextColor(0);

    // Métricas
    doc.setFontSize(12);
    doc.text("Resumen general", 14, 36);

    autoTable(doc, {
      startY: 40,
      head: [["Métrica", "Valor"]],
      body: [
        ["Productos totales", String(resumen.value.total_productos)],
        [
          "Valor del inventario",
          formatQ(resumen.value.valor_total_inventario_q),
        ],
        ["Pedidos de hoy", String(resumen.value.pedidos_del_dia)],
        ["Productos con stock bajo", String(stockBajo.value.length)],
      ],
      theme: "striped",
      headStyles: { fillColor: [40, 40, 40] },
    });

    // Tabla de stock bajo
    const yAfter = doc.lastAutoTable.finalY + 12;
    doc.setFontSize(12);
    doc.text("Alerta de stock bajo", 14, yAfter);

    if (stockBajo.value.length) {
      autoTable(doc, {
        startY: yAfter + 4,
        head: [["SKU", "Nombre", "Categoría", "Stock", "Mínimo"]],
        body: stockBajo.value.map((p) => [
          p.sku,
          p.nombre,
          p.categoria ?? "—",
          String(p.cantidad),
          String(p.stock_minimo),
        ]),
        theme: "striped",
        headStyles: { fillColor: [180, 60, 60] },
      });
    } else {
      doc.setFontSize(10);
      doc.text("No hay productos con stock bajo.", 14, yAfter + 8);
    }

    const nombreArchivo = `reporte-dashboard-${new Date()
      .toISOString()
      .slice(0, 10)}.pdf`;
    doc.save(nombreArchivo);
  } catch (e) {
    error.value = `No se pudo generar el PDF: ${e.message}`;
  } finally {
    exportando.value = false;
  }
}

onMounted(cargar);
</script>

<style scoped>
.view-header {
  margin-bottom: 1.5rem;
}
.subtitle {
  color: var(--color-ink-muted);
  margin: 0;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.metric-label {
  color: var(--color-ink-muted);
  font-size: 0.85rem;
}
.metric-value {
  font-size: 1.6rem;
  font-weight: 600;
}
.metric.alerta {
  border-color: var(--color-accent);
}
.stock-list {
  overflow-x: auto;
}
.acciones {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-start;
}
@media (max-width: 900px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
