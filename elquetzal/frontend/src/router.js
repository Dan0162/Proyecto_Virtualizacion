import { createRouter, createWebHistory } from "vue-router";
import DashboardView from "./views/DashboardView.vue";
import InventarioView from "./views/InventarioView.vue";
import PedidosView from "./views/PedidosView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "dashboard",
      component: DashboardView,
    },
    {
      path: "/inventario",
      name: "inventario",
      component: InventarioView,
    },
    {
      path: "/pedidos",
      name: "pedidos",
      component: PedidosView,
    },
  ],
});

export default router;
