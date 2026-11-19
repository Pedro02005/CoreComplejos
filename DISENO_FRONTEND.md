# Diseño del frontend de Reservas Deportivas

## Objetivo

Una interfaz sencilla para que el cliente encuentre una cancha, reserve un horario
y consulte su actividad. El código se organiza por pantallas y utiliza componentes
pequeños, CSS propio y comentarios en español para facilitar cambios durante clases.

El frontend está hecho con React y JavaScript. Los administradores utilizan Django
Admin y los clientes utilizan esta aplicación.

## Colores

Los colores principales están definidos como variables al inicio de
`frontend/src/styles.css`.

| Uso | Variable | Color | Aplicación |
| --- | --- | --- | --- |
| Principal | `--primary` | `#16704A` | Botones principales, enlaces, iconos y barras de estadísticas |
| Principal oscuro | `--primary-dark` | `#105637` | Botones al pasar el cursor y énfasis en importes |
| Principal claro | `--primary-light` | `#EAF5EE` | Menú seleccionado, etiquetas positivas e iconos |
| Secundario | `--secondary` | `#123F32` | Panel de bienvenida del login y encabezado del inicio |
| Acento | `--accent` | `#D4EFAA` | Texto destacado e ilustración sobre el fondo verde oscuro |
| Fondo general | `--background` | `#F5F7F8` | Fondo del panel del cliente |
| Superficie | `--surface` | `#FFFFFF` | Formularios, tarjetas y barra de navegación |
| Texto principal | `--text` | `#24352D` | Títulos y contenido |
| Texto secundario | `--muted` | `#61716A` | Descripciones y ayudas |
| Bordes | `--border` | `#DCE4DF` | Separación entre tarjetas, filas y controles |
| Error y cancelación | `--danger` | `#B42D35` | Cancelar y mensajes de error |
| Fondo de error | `--danger-light` | `#FFF0F0` | Alertas y estado cancelado |

El verde relaciona visualmente el deporte con las acciones de reservar y continuar.
El rojo se reserva para cancelaciones y errores. Los estados también incluyen texto,
de modo que el significado no depende solamente del color.

## Tipografía

Familia principal: **Segoe UI**, con **Arial** y **sans-serif** como alternativas.
Son fuentes del sistema y no requieren descargar archivos de tipografía.

| Elemento | Tamaño aproximado |
| --- | --- |
| Texto normal | 16 px |
| Título principal de página | Entre 27 y 34 px, según el ancho |
| Títulos de secciones | 19 px |
| Etiquetas y botones | 15 px |
| Ayudas y datos secundarios | 14 px |
| Título decorativo del login en computadora | Entre 43 y 64 px |

Los títulos y botones usan mayor peso. Los textos normales mantienen una altura de
línea de 1.55 para facilitar la lectura. Los tamaños se expresan principalmente en `rem`.

## Distribución

### Login y registro

En computadora se muestran dos columnas: una presentación verde oscura a la izquierda
y el formulario sobre blanco a la derecha. La ilustración de cancha está hecha con
CSS, sin imágenes externas. En pantallas pequeñas se muestra el formulario con la marca.

La página inicial dirige al login cuando no hay sesión. El registro es accesible desde
el enlace "Crea tu cuenta". Después de registrarse se vuelve al login con una confirmación.

### Panel del cliente

En computadora hay una barra lateral de 238 px, una cabecera con el nombre del cliente
y el contenido de la página. En celular la navegación se abre mediante un botón de menú.

El menú contiene:

- Mi inicio.
- Reservar cancha.
- Mis reservas.
- Encuestas.
- Mis beneficios.
- Mis estadísticas.
- Mi perfil.
- Cerrar sesión.

Las tarjetas tienen bordes suaves y esquinas de 12 px. Los botones y campos utilizan
esquinas de 8 px. La separación habitual entre bloques es de 16 a 24 px.

## Contenido de cada pantalla

| Pantalla | Contenido |
| --- | --- |
| Mi inicio | Bienvenida, próximas reservas, encuestas pendientes y conteos de beneficios |
| Complejos | Búsqueda por nombre y ciudad, tarjetas y paginación |
| Complejo | Información general y canchas filtrables por deporte |
| Cancha | Horarios, tarifas, fecha, duración, promoción y cotización antes de confirmar |
| Mis reservas | Filtros por próximas, finalizadas y canceladas |
| Detalle de reserva | Datos, precio, tarifas, historial y formulario de cancelación |
| Encuestas | Formularios de cancelación y experiencia |
| Mis beneficios | Promociones disponibles, utilizadas y recomendaciones |
| Mis estadísticas | Período, conteos, preferencias, calificaciones y barras por motivo de cancelación |
| Mi perfil | Datos personales y formulario de actualización |

Las recomendaciones muestran explicaciones para el cliente, sin exponer los códigos
internos de las reglas. Las estadísticas contienen datos personales calculados por
Django; no hay datos inventados cuando falta historial.

## Adaptación a distintos tamaños

- Las tarjetas del catálogo pasan de tres a dos y luego a una columna.
- Las estadísticas pasan de cuatro a dos columnas.
- La cotización se coloca al lado de los horarios en computadora y debajo en celular.
- Las tablas permiten desplazamiento horizontal dentro de su propio contenedor.
- Los formularios de nombres y apellidos pasan a una columna en pantallas pequeñas.
- El menú móvil cerrado queda oculto también para la navegación por teclado.

## Mensajes e interacción

Las pantallas muestran estados de carga, confirmaciones, errores y mensajes cuando
no hay resultados. Los botones de envío se deshabilitan mientras termina una operación.
Antes de cancelar una reserva se solicita confirmación mediante un formulario.

Los campos tienen etiquetas, los controles muestran foco visible y las animaciones
respetan la preferencia de movimiento reducido. Los iconos SVG son decorativos y están
acompañados de texto.

Las fechas usan la zona `America/Guayaquil` y los precios se muestran en USD.
El estado "Finalizada" se obtiene del horario de una reserva confirmada cuyo encuentro
ya terminó; no añade un estado nuevo al modelo de Django.

## Dónde hacer cambios durante clases

| Cambio | Archivo |
| --- | --- |
| Colores, fuentes, espacios y tamaños | `frontend/src/styles.css` |
| Menú y encabezado | `frontend/src/components/Layout.jsx` |
| Rutas y pantallas protegidas | `frontend/src/App.jsx` |
| Login y registro | `frontend/src/pages/AuthPages.jsx` |
| Catálogo y complejos | `frontend/src/pages/CatalogoPages.jsx` |
| Disponibilidad y reserva | `frontend/src/pages/CanchaPage.jsx` |
| Consultas al backend | `frontend/src/services/api.js` |
| Zona horaria, formato de dinero y etiquetas | `frontend/src/utils.js` |
| Dirección del backend | `VITE_API_URL` en `frontend/.env` |

Por ejemplo, cambiar `--primary` modifica el color principal de botones, enlaces e
iconos sin editar cada pantalla. Para cambiar el texto del título de una sección,
se edita su componente dentro de `pages/`.
