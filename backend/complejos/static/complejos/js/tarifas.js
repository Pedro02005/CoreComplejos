document.addEventListener("DOMContentLoaded", function () {
    const complejo = document.getElementById("id_complejo");
    const cancha = document.getElementById("id_cancha");

    if (!complejo || !cancha) return;

    complejo.addEventListener("change", async function () {
        const complejoId = complejo.value;
        cancha.replaceChildren(new Option("Seleccione una cancha", ""));

        if (!complejoId) {
            cancha.disabled = false;
            return;
        }

        cancha.disabled = true;
        const url = "/admin/complejos/tarifa/canchas-por-complejo/?complejo_id="
            + encodeURIComponent(complejoId);

        try {
            const respuesta = await fetch(url);
            if (!respuesta.ok) throw new Error("No se pudieron cargar las canchas.");

            const datos = await respuesta.json();
            // Evita mostrar resultados de una selección anterior.
            if (complejo.value !== complejoId) return;

            datos.canchas.forEach(function (item) {
                cancha.add(new Option(item.nombre, item.id));
            });
        } catch (error) {
            if (complejo.value === complejoId) {
                console.error(error);
                alert("No se pudieron cargar las canchas.");
            }
        } finally {
            if (complejo.value === complejoId) cancha.disabled = false;
        }
    });
});
