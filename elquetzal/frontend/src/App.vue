<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">EQ</span>
        <span class="brand-name">El Quetzal</span>
      </div>
      <nav>
        <RouterLink to="/" class="nav-link">Dashboard</RouterLink>
        <RouterLink to="/inventario" class="nav-link">Inventario</RouterLink>
        <RouterLink to="/pedidos" class="nav-link">Pedidos</RouterLink>
      </nav>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from "vue-router";
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 220px 1fr;
  min-height: 100%;
}

.sidebar {
  background: var(--color-primary);
  color: #fff;
  padding: 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.brand-mark {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 4px;
  padding: 0.15rem 0.4rem;
}

.brand-name {
  font-weight: 600;
  font-size: 1.05rem;
}

nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-link {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.9rem;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.nav-link.router-link-exact-active {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-weight: 500;
}

.content {
  padding: 2rem 2.5rem;
}

@media (max-width: 720px) {
  .shell {
    grid-template-columns: 1fr;
  }
  .sidebar {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
  nav {
    flex-direction: row;
  }
}
</style>
