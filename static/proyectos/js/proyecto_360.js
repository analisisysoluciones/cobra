document.addEventListener("DOMContentLoaded", function () {

    const proyectoId = document.getElementById("proyecto-id").value;

    const bloques = [

        {
            id: "bloque-finanzas",
            url: window.proyecto360Urls.finanzas
        },

        // {
        //     id: "bloque-actividades",
        //     url: window.proyecto360Urls.actividades
        // },

        {
             id: "bloque-compras",
             url: window.proyecto360Urls.compras
        },

        {
             id: "bloque-nomina",
             url: window.proyecto360Urls.nomina
        },

        // {
        //     id: "bloque-clientes",
        //     url: window.proyecto360Urls.clientes
        // }

    ];
    bloques.forEach(bloque => cargarBloque(bloque.id, bloque.url));

});


function cargarBloque(contenedorId, url) {

    const contenedor = document.getElementById(contenedorId);

    fetch(url, {
        method: "GET",
        headers: {
            "X-Requested-With": "XMLHttpRequest"
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Error HTTP " + response.status);
        }
        return response.text();
    })
    .then(html => {
        contenedor.innerHTML = html;
    })
    .catch(error => {
        contenedor.innerHTML = `
            <div class="card-body text-center text-danger">
                Error al cargar bloque
            </div>
        `;
        console.error(error);
    });
}

