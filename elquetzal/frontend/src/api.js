const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let detail = "";

    try {
      const body = await res.json();
      detail = body.error || body.message || "";
    } catch {}

    throw new Error(
      detail || `Error ${res.status} al llamar ${path}`
    );
  }

  if (res.status === 204) {
    return null;
  }

  return res.json();
}

export const catalogoApi = {
  listar: async () => {
    const data = await request("/catalogo/productos");
    return data.productos ?? [];
  },

  crear: (producto) =>
    request("/catalogo/productos", {
      method: "POST",
      body: JSON.stringify(producto),
    }),

  actualizar: (sku, producto) =>
    request(`/catalogo/productos/${encodeURIComponent(sku)}`, {
      method: "PUT",
      body: JSON.stringify(producto),
    }),

  eliminar: (sku) =>
    request(`/catalogo/productos/${encodeURIComponent(sku)}`, {
      method: "DELETE",
    }),
};

export const inventarioApi = {
  listar: async () => {
    const data = await request("/inventario/stock");
    return data.stock ?? [];
  },

  obtener: (sku) =>
    request(`/inventario/stock/${encodeURIComponent(sku)}`),

  crear: (stock) =>
    request("/inventario/stock", {
      method: "POST",
      body: JSON.stringify(stock),
    }),

  actualizar: (sku, stock) =>
    request(`/inventario/stock/${encodeURIComponent(sku)}`, {
      method: "PUT",
      body: JSON.stringify(stock),
    }),

  eliminar: (sku) =>
    request(`/inventario/stock/${encodeURIComponent(sku)}`, {
      method: "DELETE",
    }),
};

export const clientesApi = {
  listar: async () => {
    const data = await request("/clientes/");
    return data.clientes ?? [];
  },

  obtener: (id) =>
    request(`/clientes/${id}`),

  crear: (cliente) =>
    request("/clientes/", {
      method: "POST",
      body: JSON.stringify(cliente),
    }),

  actualizar: (id, cliente) =>
    request(`/clientes/${id}`, {
      method: "PUT",
      body: JSON.stringify(cliente),
    }),

  eliminar: (id) =>
    request(`/clientes/${id}`, {
      method: "DELETE",
    }),
};

export const pedidosApi = {
  listar: async () => {
    const data = await request("/pedidos/");
    return data.pedidos ?? [];
  },

  crear: (pedido) =>
    request("/pedidos/", {
      method: "POST",
      body: JSON.stringify(pedido),
    }),

  actualizarEstado: (id, estado) =>
    request(`/pedidos/${id}/estado`, {
      method: "PATCH",
      body: JSON.stringify({ estado }),
    }),
};

export const reportesApi = {
  resumen: () =>
    request("/reportes/"),
};
