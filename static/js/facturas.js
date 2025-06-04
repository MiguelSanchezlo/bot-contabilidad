function showLoading(texto) {
  setLoadingText(texto);
  const overlay = document.getElementById("loading-overlay");
  if (!overlay) return;

  // 1) Quitamos d-none y agregamos d-flex para que se muestre en modo flex:
  overlay.classList.remove("d-none");
  overlay.classList.add("d-flex");
  toggleButtons(true);
}

function hideLoading() {
  const overlay = document.getElementById("loading-overlay");
  if (!overlay) return;

  // 2) Quitamos d-flex y volvemos a poner d-none para ocultar:
  overlay.classList.remove("d-flex");
  overlay.classList.add("d-none");

  window.onbeforeunload = null;
  toggleButtons(false);
}

function setLoadingText(texto) {
  const loadingText = document.getElementById("loading-text");
  if (loadingText) loadingText.innerText = texto;
}


function toggleButtons(disabled) {
  document.querySelectorAll("button[data-bs-toggle='tooltip']").forEach(btn => {
    btn.disabled = disabled;
  });
  const submitBtn = document.querySelector("#form-filtrar button[type='submit']");
  if (submitBtn) submitBtn.disabled = disabled;
}

// Ahora escuchamos window.onload para ocultar el overlay apenas termine de cargar todo:
window.addEventListener("load", function () {
  hideLoading();
});

// Y en DOMContentLoaded solo atamos listeners; NO volvemos a llamar showLoading/​hideLoading aquí a secas:
document.addEventListener("DOMContentLoaded", function () {
  console.log("🔧 facturas.js cargado y DOM listo");

  // ─── Inicializar tooltips de Bootstrap ───
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // ─── Confirmación antes de eliminar fila ───
  function activarBotonesEliminar() {
    document.querySelectorAll(".eliminar-btn").forEach((btn) => {
      btn.addEventListener("click", function () {
        const confirmado = confirm("¿Seguro que deseas eliminar esta fila?");
        if (confirmado) {
          this.closest("tr").remove();
        }
      });
    });
  }
  activarBotonesEliminar();

  // ─── Restaurar tablas ───
  const btnRestaurar = document.getElementById("restaurar-tablas");
  if (btnRestaurar) {
    btnRestaurar.addEventListener("click", function () {
      const fmBackup = document.getElementById("tabla-fm-backup");
      const fbBackup = document.getElementById("tabla-fb-backup");
      if (fmBackup && fbBackup) {
        document.getElementById("tabla-fm").innerHTML = fmBackup.innerHTML;
        document.getElementById("tabla-fb").innerHTML = fbBackup.innerHTML;
        activarBotonesEliminar();
        showToast("Tablas restauradas", "info");
      }
    });
  }

  // ─── Buscador en tiempo real ───
  const buscador = document.getElementById("buscador");
  if (buscador) {
    buscador.addEventListener("input", function () {
      const texto = this.value.trim().toLowerCase();
      document.querySelectorAll("#tabla-fm tr, #tabla-fb tr").forEach(tr => {
        const filaText = tr.innerText.trim().toLowerCase();
        tr.style.display = filaText.includes(texto) ? "" : "none";
      });
    });
  }

  // ─── Exportar facturas visibles a Excel (rápido, sin spinner) ───
  const btnExportVisible = document.getElementById("exportar-visible");
  if (btnExportVisible) {
    btnExportVisible.addEventListener("click", function () {
      function tableToSheet(tableId) {
        const table = document.getElementById(tableId).closest("table");
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.table_to_sheet(table, { raw: true });
        XLSX.utils.book_append_sheet(wb, ws, tableId.toUpperCase());
        return wb;
      }
      const wb_fm = tableToSheet("tabla-fm");
      const wb_fb = tableToSheet("tabla-fb");
      const wb = XLSX.utils.book_new();
      const hoy = new Date();
      const dd = String(hoy.getDate()).padStart(2, "0");
      const mm = String(hoy.getMonth() + 1).padStart(2, "0");
      const yyyy = hoy.getFullYear();
      const fechaStr = `${dd}-${mm}-${yyyy}`;
      wb.SheetNames = [...wb_fm.SheetNames, ...wb_fb.SheetNames];
      wb.Sheets = { ...wb_fm.Sheets, ...wb_fb.Sheets };
      XLSX.writeFile(wb, `Facturas_visibles_${fechaStr}.xlsx`);
      showToast("Descarga de Excel iniciada", "success");
    });
  }

  // ─── Asignar numeración (FM/FB) ───
  const btnAsignar = document.getElementById("asignar-numeracion");
  if (btnAsignar) {
    btnAsignar.addEventListener("click", function () {
      showLoading("Asignando numeración...");

      setTimeout(() => {
        let fmStart = parseInt(document.getElementById("inicio-fm").value) || 0;
        let fbStart = parseInt(document.getElementById("inicio-fb").value) || 0;
        const asignarPorGrupo = (tbodyId, tipoFactura, numeroInicial) => {
          let contador = numeroInicial;
          const grupos = {};
          document.querySelectorAll(`#${tbodyId} tr`).forEach((row) => {
            const cells = row.querySelectorAll("td");
            if (cells.length >= 7) {
              const orden = cells[6].innerText.trim().toUpperCase();
              if (orden.startsWith(tipoFactura)) {
                if (!grupos[orden]) {
                  contador++;
                  grupos[orden] = contador;
                }
                cells[3].innerText = grupos[orden];
              }
            }
          });
        };
        asignarPorGrupo("tabla-fm", "FM", fmStart);
        asignarPorGrupo("tabla-fb", "FB", fbStart);

        hideLoading();
        showToast("Numeración asignada", "success");
      }, 300);
      // ← No llamamos hideLoading() aquí
    });
  }

  // ─── Subir facturas a Dataico (fetch + spinner + toasts) ───
  const btnSubir = document.getElementById("subir-dataico");
  if (btnSubir) {
    btnSubir.addEventListener("click", function () {
      const parseTable = (tbodyId) => {
        const tbody = document.getElementById(tbodyId);
        if (!tbody) return [];
        const table = tbody.closest("table");
        const headers = Array.from(table.querySelectorAll("thead th"))
          .slice(1)
          .map((h) => h.innerText.trim());
        const rows = [];
        tbody.querySelectorAll("tr").forEach((tr) => {
          const cells = tr.querySelectorAll("td");
          if (cells.length === headers.length + 1) {
            const row = {};
            headers.forEach((header, i) => {
              row[header] = cells[i + 1].innerText.trim();
            });
            rows.push(row);
          }
        });
        return rows;
      };

      const fm = parseTable("tabla-fm");
      const fb = parseTable("tabla-fb");
      const facturas = fm.concat(fb);
      if (facturas.length === 0) {
        showToast("No hay facturas para enviar", "warning");
        return;
      }

      showLoading("Subiendo facturas a Dataico...");

      fetch("/facturas/subir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(facturas),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            showToast(data.message || "Facturas subidas con éxito", "success");
          } else {
            throw new Error(data.message || "Error desconocido");
          }
        })
        .catch((err) => {
          showToast("Error al subir a Dataico: " + err.message, "danger");
        })
        .finally(() => {
          hideLoading();
        });
    });
  }

  // ─── Traer facturas desde Dataico (fetch + spinner + toasts) ───
  const btnTraer = document.getElementById("traer-dataico");
  if (btnTraer) {
    btnTraer.addEventListener("click", async () => {
      const tablaFmElem = document.getElementById("tabla-fm");
      if (!tablaFmElem) {
        showToast("Tabla FM no encontrada", "warning");
        return;
      }
      const tablaFm = tablaFmElem.closest("table");
      const ths = Array.from(tablaFm.querySelectorAll("thead th"));
      const numIdx = ths.findIndex((h) => h.textContent.trim() === "NUMERO");
      const orderIdx = ths.findIndex((h) => h.textContent.trim() === "ORDEN_DE_COMPRA");
      if (numIdx < 0 || orderIdx < 0) {
        showToast("No encuentro las columnas NUMERO u ORDEN_DE_COMPRA", "warning");
        return;
      }

      const pares = [];
      document.querySelectorAll("#tabla-fm tr, #tabla-fb tr").forEach((tr) => {
        const cells = tr.querySelectorAll("td");
        const orden = cells[orderIdx]?.textContent.trim().toUpperCase();
        const numero = cells[numIdx]?.textContent.trim();
        if (orden && numero) pares.push({ orden, numero });
      });
      if (!pares.length) {
        showToast("No hay facturas para traer de Dataico", "warning");
        return;
      }

      const PREFIX = "MCFE";
      let fetchNums = pares.map(({ orden, numero }) =>
        orden.startsWith("FM") ? `${PREFIX}${numero}` : numero
      );
      fetchNums = Array.from(new Set(fetchNums));

      showLoading("Trayendo facturas desde Dataico...");

      let data;
      try {
        const resp = await fetch("/facturas/dataico", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ numeros: fetchNums }),
        });
        data = await resp.json();
      } catch (err) {
        hideLoading();
        showToast("Error de red al traer de Dataico: " + err.message, "danger");
        return;
      }

      if (!data.success) {
        hideLoading();
        showToast("Error al traer de Dataico: " + (data.message || ""), "danger");
        return;
      }

      // Pinta la tabla con lo recibido
      const section = document.getElementById("section-dataico");
      const tabla = document.getElementById("tabla-dataico");
      if (!tabla || !section) {
        hideLoading();
        showToast("Se esperaba tabla de Dataico pero no se encontró", "warning");
        return;
      }
      const theadTr = tabla.querySelector("thead tr");
      const tbody = tabla.querySelector("tbody");
      theadTr.innerHTML = "<th>Acción</th>";
      tbody.innerHTML = "";
      data.items.forEach((item, idx) => {
        if (idx === 0) {
          Object.keys(item).forEach((k) => {
            const th = document.createElement("th");
            th.textContent = k;
            th.setAttribute("data-bs-toggle", "tooltip");
            th.setAttribute("title", k);
            theadTr.appendChild(th);
          });
        }
        const tr = document.createElement("tr");
        tr.innerHTML =
          `<td>
              <button class="btn btn-sm btn-danger eliminar-btn" data-bs-toggle="tooltip" title="Eliminar esta fila">
                Eliminar
              </button>
           </td>` +
          Object.values(item)
            .map((v) => `<td>${v}</td>`)
            .join("");
        tbody.appendChild(tr);
      });
      section.style.display = "block";
      activarBotonesEliminar();
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
      });

      hideLoading();
      showToast("Facturas traídas de Dataico", "success");
    });
  }

  // ─── Exportar a Contapyme (fetch + spinner + toasts) ───
  const btnExportContapyme = document.getElementById("export-contapyme");
  if (btnExportContapyme) {
    btnExportContapyme.addEventListener("click", async () => {
      const tabla = document.getElementById("tabla-dataico");
      if (!tabla) {
        showToast("No se encontró la tabla de Dataico", "warning");
        return;
      }

      const headers = Array.from(tabla.querySelectorAll("thead th")).slice(1).map((th) =>
        th.textContent.trim()
      );
      const items = [];
      tabla.querySelectorAll("tbody tr").forEach((tr) => {
        const celdas = tr.querySelectorAll("td");
        if (celdas.length < headers.length + 1) return;
        const item = {};
        headers.forEach((key, i) => {
          item[key] = celdas[i + 1].textContent.trim();
        });
        items.push(item);
      });
      if (!items.length) {
        showToast("No hay datos válidos en la tabla para exportar", "warning");
        return;
      }

      showLoading("Exportando a Contapyme...");

      try {
        const resp = await fetch("/facturas/contapyme-export", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ numeros: items }),
        });
        if (!resp.ok) {
          const errorJson = await resp.json().catch(() => ({}));
          throw new Error(errorJson.message || resp.status);
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const hoy = new Date();
        const dd = String(hoy.getDate()).padStart(2, "0");
        const mm = String(hoy.getMonth() + 1).padStart(2, "0");
        const yyyy = hoy.getFullYear();
        const fechaStr = `${dd}-${mm}-${yyyy}`;
        a.download = `contapyme_${fechaStr}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);

        showToast("Descarga Contapyme iniciada", "success");
      } catch (e) {
        showToast("Error exportando a Contapyme: " + e.message, "danger");
      } finally {
        hideLoading();
      }
    });
  }

  // ─── Mostrar spinner al filtrar por fecha (submit del form) ───
  const formFiltrar = document.getElementById("form-filtrar");
  if (formFiltrar) {
    formFiltrar.addEventListener("submit", function () {
      showLoading("Cargando facturas de la base de datos...");
    });
  }
});
