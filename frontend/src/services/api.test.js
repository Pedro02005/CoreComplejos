import test, { afterEach, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { guardarTokens, obtenerTokens, solicitar } from './api.js';

const fetchOriginal = globalThis.fetch;
beforeEach(() => {
  const valores = new Map();
  globalThis.sessionStorage = {
    getItem: (clave) => valores.get(clave) || null,
    setItem: (clave, valor) => valores.set(clave, valor),
    removeItem: (clave) => valores.delete(clave),
  };
  globalThis.window = new EventTarget();
});
afterEach(() => {
  globalThis.fetch = fetchOriginal;
  delete globalThis.sessionStorage;
  delete globalThis.window;
});

test('consultas simultáneas con acceso vencido comparten una renovación JWT', async () => {
  guardarTokens({ access: 'vencido', refresh: 'renovable' });
  let renovaciones = 0;
  globalThis.fetch = async (url, opciones) => {
    if (url.endsWith('/token/refresh/')) {
      renovaciones += 1;
      await new Promise((resolver) => setTimeout(resolver, 10));
      return Response.json({ access: 'nuevo' });
    }
    return opciones.headers.Authorization === 'Bearer nuevo'
      ? Response.json({ correcto: true })
      : Response.json({ detail: 'Vencido' }, { status: 401 });
  };
  const resultados = await Promise.all([solicitar('/cuentas/perfil/'), solicitar('/reservas/')]);
  assert.equal(renovaciones, 1);
  assert.deepEqual(resultados, [{ correcto: true }, { correcto: true }]);
  assert.equal(obtenerTokens().access, 'nuevo');
});

test('una sesión que ya no puede renovarse se elimina y avisa al contexto', async () => {
  guardarTokens({ access: 'vencido', refresh: 'vencido' });
  let avisos = 0;
  window.addEventListener('sesion-vencida', () => {
    avisos += 1;
  });
  globalThis.fetch = async () => Response.json({ detail: 'Sesión vencida' }, { status: 401 });
  await assert.rejects(solicitar('/cuentas/perfil/'), /Sesión vencida/);
  assert.equal(obtenerTokens(), null);
  assert.equal(avisos, 1);
});

test('una caída de conexión no elimina la sesión existente', async () => {
  guardarTokens({ access: 'valido', refresh: 'valido' });
  globalThis.fetch = async () => {
    throw new TypeError('Network unavailable');
  };
  await assert.rejects(solicitar('/reservas/'), /No se pudo conectar/);
  assert.equal(obtenerTokens().access, 'valido');
});

test('el login público no envía credenciales de una sesión previa', async () => {
  guardarTokens({ access: 'anterior', refresh: 'anterior' });
  globalThis.fetch = async (_url, opciones) => {
    assert.equal(opciones.headers.Authorization, undefined);
    return Response.json({ detail: 'Usuario o contraseña incorrectos' }, { status: 401 });
  };
  await assert.rejects(
    solicitar('/token/', { method: 'POST', body: {}, autenticado: false }),
    /incorrectos/
  );
  assert.equal(obtenerTokens().access, 'anterior');
});
