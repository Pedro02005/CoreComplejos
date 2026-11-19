import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { cuentasApi } from '../services/api';
import { ErrorMessage, Icon, PageHeader, SuccessMessage } from '../components/UI';

export default function PerfilPage() {
  const { usuario, setUsuario } = useAuth();
  const [datos, setDatos] = useState({ first_name: usuario.first_name, last_name: usuario.last_name, email: usuario.email, cedula: usuario.cedula || '', telefono: usuario.telefono || '' });
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [enviando, setEnviando] = useState(false);
  const campo = (nombre) => ({ value: datos[nombre], onChange: (e) => { setDatos({ ...datos, [nombre]: e.target.value }); setMensaje(''); } });
  async function guardar(evento) {
    evento.preventDefault(); setError(''); setMensaje(''); setEnviando(true);
    try { setUsuario(await cuentasApi.guardarPerfil(datos)); setMensaje('Tus datos se actualizaron correctamente.'); }
    catch (err) { setError(err.message); }
    finally { setEnviando(false); }
  }
  return <><PageHeader titulo="Mi perfil" descripcion="Mantén tus datos personales actualizados." /><div className="profile-grid"><aside className="panel profile-card"><span className="profile-avatar"><Icon name="user" size={42} /></span><h2>{usuario.first_name || usuario.username} {usuario.last_name}</h2><p>@{usuario.username}</p><span className="badge badge-green">Cuenta de cliente</span></aside><section className="panel"><h2>Datos personales</h2><p className="muted">Tu nombre de usuario es <strong>{usuario.username}</strong>.</p><ErrorMessage mensaje={error} /><SuccessMessage mensaje={mensaje} /><form className="form-stack" onSubmit={guardar}><fieldset className="form-stack" disabled={enviando}><div className="form-grid"><label>Nombres<input {...campo('first_name')} autoComplete="given-name" maxLength={150} required /></label><label>Apellidos<input {...campo('last_name')} autoComplete="family-name" maxLength={150} required /></label></div><label>Correo electrónico<input {...campo('email')} type="email" autoComplete="email" maxLength={254} required /></label><div className="form-grid"><label>Cédula <small>(opcional)</small><input {...campo('cedula')} inputMode="numeric" pattern="[0-9]{10}" maxLength={10} /></label><label>Celular <small>(opcional)</small><input {...campo('telefono')} type="tel" autoComplete="tel" pattern="09[0-9]{8}" maxLength={10} placeholder="09XXXXXXXX" /></label></div><div><button className="button primary" disabled={enviando}>{enviando ? 'Guardando…' : 'Guardar cambios'}</button></div></fieldset></form></section></div></>;
}
