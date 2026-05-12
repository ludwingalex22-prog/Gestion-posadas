document.addEventListener("DOMContentLoaded", function () {
    const fechaEntrada = document.querySelector("[name='fecha_entrada']");
    const fechaSalida = document.querySelector("[name='fecha_salida']");

    if (fechaEntrada && fechaSalida) {
        fechaEntrada.addEventListener("change", function () {
            fechaSalida.min = fechaEntrada.value;

            if (fechaSalida.value && fechaSalida.value <= fechaEntrada.value) {
                fechaSalida.value = "";
            }
        });
    }

    const formularioPago = document.querySelector("#formularioPagoCliente");
    const montoRecibido = document.querySelector("#id_monto_recibido");
    const montoRecibidoVista = document.querySelector("#montoRecibidoVista");
    const cambioVista = document.querySelector("#cambioVista");

    if (formularioPago && montoRecibido && montoRecibidoVista && cambioVista) {
        const total = parseFloat(formularioPago.dataset.totalPago || "0");

        function actualizarResumenPago() {
            const recibido = parseFloat(montoRecibido.value || "0");
            const cambio = Math.max(recibido - total, 0);

            montoRecibidoVista.textContent = `Q ${recibido.toFixed(2)}`;
            cambioVista.textContent = `Q ${cambio.toFixed(2)}`;
        }

        montoRecibido.addEventListener("input", actualizarResumenPago);
        actualizarResumenPago();
    }
});
