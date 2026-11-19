import test from 'node:test';
import assert from 'node:assert/strict';
import { estadoReserva, fechaLocal, puedeCancelar } from './utils.js';

test('la fecha del formulario usa Ecuador incluso cuando en UTC ya es el siguiente día', () => {
  assert.equal(fechaLocal(new Date('2026-11-20T02:00:00Z')), '2026-11-19');
});

const reserva = {
  estado: 'CONFIRMADA',
  inicio: '2026-11-22T17:00:00-05:00',
  fin: '2026-11-22T18:00:00-05:00',
  cancelable_hasta: '2026-11-22T05:00:00-05:00',
};
test('el estado visual distingue encuentro próximo, en curso, finalizado y cancelado', () => {
  assert.equal(estadoReserva(reserva, Date.parse('2026-11-22T16:00:00-05:00')), 'Confirmada');
  assert.equal(estadoReserva(reserva, Date.parse(reserva.inicio)), 'En curso');
  assert.equal(estadoReserva(reserva, Date.parse(reserva.fin)), 'Finalizada');
  assert.equal(
    estadoReserva({ ...reserva, estado: 'CANCELADA' }, Date.parse(reserva.fin)),
    'Cancelada'
  );
});
test('la interfaz respeta el límite de cancelación y las reservas canceladas', () => {
  const limite = Date.parse(reserva.cancelable_hasta);
  assert.equal(puedeCancelar(reserva, limite), true);
  assert.equal(puedeCancelar(reserva, limite + 1), false);
  assert.equal(puedeCancelar({ ...reserva, estado: 'CANCELADA' }, limite - 1000), false);
});
