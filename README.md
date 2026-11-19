# Reservas Deportivas

Aplicación con backend Django REST Framework y frontend React. Los clientes utilizan
React para reservar y consultar su actividad; los administradores utilizan Django Admin.

## Ejecutar en Windows

Se necesitan PostgreSQL configurado, el entorno virtual del backend y Node.js compatible
con Vite 8. El proyecto se verificó con Node.js 24.

Abrir dos terminales desde la carpeta `ReservasDeportivas`.

### Terminal 1: backend

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

La conexión PostgreSQL se configura en `backend/.env`. Hay una referencia en
`backend/.env.example`. El proyecto existente conserva su configuración local.

### Terminal 2: frontend

```powershell
cd frontend
npm ci
npm run dev
```

Abrir **http://127.0.0.1:5173/**. Sin sesión, se muestra el login. Desde allí se puede
crear una cuenta de cliente. Django se ejecuta en **http://127.0.0.1:8000/** y su
administración está en **http://127.0.0.1:8000/admin/**.

Si las dependencias ya están instaladas, basta con ejecutar `runserver` y `npm run dev`.

## Configuración del frontend

Por defecto, la API es `http://127.0.0.1:8000/api`. Para cambiarla, copiar
`frontend/.env.example` a `frontend/.env`, editar `VITE_API_URL` y reiniciar Vite.

El backend permite los orígenes locales `http://localhost:5173` y
`http://127.0.0.1:5173`. Para utilizar otro origen, configurar `FRONTEND_ORIGINS` en
`backend/.env`, separando varios valores por comas, y reiniciar Django.

Los puertos del frontend son fijos: si 5173 ya está ocupado, hay que detener la instancia
anterior antes de ejecutar otra. La configuración no permite silenciosamente cualquier origen.

## Funciones del cliente

- Registro con validación de usuario, correo, contraseña y datos de contacto opcionales.
- Inicio de sesión con JWT, renovación de acceso y cierre de sesión de la pestaña.
- Catálogo de complejos, canchas, horarios y tarifas.
- Consulta de disponibilidad, cotización por franjas y reserva con promoción opcional.
- Listado, detalle, historial y cancelación de reservas.
- Encuestas de cancelación y de experiencia.
- Promociones disponibles y utilizadas, recomendaciones y actualización de beneficios.
- Estadísticas personales de los últimos 30, 90, 180 o 365 días.
- Consulta y edición del perfil propio.

El catálogo necesita complejos y canchas activos con horarios y tarifas configurados
desde Django Admin. Las promociones requieren campañas vigentes y condiciones cumplidas
por el historial o las encuestas del cliente. Una cuenta nueva mostrará estados vacíos
hasta que tenga actividad.

Los administradores no utilizan el panel del cliente. Si inician sesión allí, se muestra
el enlace hacia Django Admin, donde ingresan con sus credenciales administrativas.

## Endpoints añadidos para React

| Método | Ruta | Acceso |
| --- | --- | --- |
| POST | `/api/cuentas/registro/` | Público; siempre crea clientes |
| GET | `/api/cuentas/perfil/` | Usuario autenticado |
| PATCH | `/api/cuentas/perfil/` | Solo datos personales de la cuenta autenticada |
| GET | `/api/estadisticas/?dias=90` | Estadísticas del usuario autenticado |

El login y la renovación usan `/api/token/` y `/api/token/refresh/`. El registro recibe
`username`, `first_name`, `last_name`, `email`, `password`, `password_confirmacion`,
y opcionalmente `cedula` y `telefono`. El perfil permite modificar nombres, apellidos,
correo, cédula y teléfono. Los roles y privilegios se administran en Django Admin.

## Estructura del frontend

```text
frontend/src/
  components/   Menú, tarjetas, mensajes y elementos compartidos
  context/      Sesión del usuario
  hooks/        Carga de datos y control de errores
  pages/        Una pantalla por función
  services/     Llamadas a la API y renovación JWT
  utils.js      Fechas de Ecuador, dinero y estados de reservas
  styles.css    Colores y estilos de toda la aplicación
  App.jsx       Rutas y acceso a las pantallas
```

Los JWT se conservan en `sessionStorage` durante la sesión de la pestaña. Cerrar sesión
los elimina del navegador. Ante una expiración se intenta renovar el acceso y, si la
renovación ya no es válida, se solicita iniciar sesión nuevamente. Una caída de conexión
permite reintentar sin borrar la sesión.

## Pruebas y compilación

Desde `backend/`:

```powershell
.\venv\Scripts\python.exe manage.py test
.\venv\Scripts\python.exe manage.py check
```

Desde `frontend/`:

```powershell
npm test
npm run build
```

El build se genera en `frontend/dist/`. Para inspeccionarlo localmente se puede usar
`npm run preview`, que abre el puerto 4173; ese origen debe agregarse a `FRONTEND_ORIGINS`
si se desean consultar datos desde la previsualización del build.

La revisión visual se realizó con una base de pruebas separada y datos ficticios. No se
añadieron cuentas de demostración a la base normal.

## Documentación

- [Diseño visual, colores, tipografía y cambios en clase](DISENO_FRONTEND.md).
- [Catálogo por API](backend/complejos/README.md).
- [Roles y administración](backend/cuentas/README.md).
