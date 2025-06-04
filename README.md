# bot-contabilidad

Bot para automatizar la facturación electrónica (Ofima - Dataico - Contapyme) para Micelu.co.

## Descripción

Este proyecto extrae facturas de la base de datos Ofima en SQL Server, las prepara siguiendo las reglas UVT/IVA definidas por el area de contabilidad, y luego:

1. Muestra las facturas en una interfaz web (Flask + Bootstrap + DataTables).
2. Permite exportar a Excel las facturas visibles.
3. Sube grupos de facturas a Dataico a través de su API.
4. Trae datos actualizados de Dataico.
5. Prepara un archivo exportable para Contapyme.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/MiguelSanchezlo/bot-contabilidad.git
   cd bot-contabilidad

2. Crea un entorno virtual e instala dependencias:
   ```bash
    python -m venv venv
    venv\Scripts\activate

    pip install -r requirements.txt

4. Crear un archivo .env raiz con las credenciales:
   ```bash
   SQLSERVER_USER=
   SQLSERVER_PASSWORD=
   SQLSERVER_HOST=
   SQLSERVER_DB=
   SQLSERVER_DRIVER=
   DATAICO_ACCOUNT_ID=
   DATAICO_AUTH_TOKEN=
   DATAICO_PREFIX_FM=
   DATAICO_RESOLUTION_FM=
   DATAICO_PREFIX_FB=
   DATAICO_RESOLUTION_FB=
