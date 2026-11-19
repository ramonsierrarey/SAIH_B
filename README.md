# Monitor de El Burguillo

Aplicación Streamlit para consultar y mostrar los datos del [SAIH Tajo](https://saihtajo.chtajo.es/tiemporeal): **El Burguillo (E_17)**, **Puerto del Pico (PN34)**, **Alberche en Navaluenga (AR21)** y **Charco del Cura (E_18)**. Consulta al abrirse y, mientras haya sesiones activas, aproximadamente una vez por hora. Permite solicitar una actualización manual (máximo una por minuto, compartido entre usuarios de la misma instancia). Los datos se mantienen solo en memoria; no se guardan en disco.

La vista incluye precipitación horaria y acumulada de 24 horas en Puerto del Pico, nivel y caudal en Navaluenga y porcentaje y salida al río de Charco del Cura. Las tarjetas muestran la tendencia respecto a la primera lectura disponible en las 25 horas anteriores. En el gráfico se pueden seleccionar estas y otras señales disponibles.

Si la última lectura del porcentaje de Charco del Cura supera el 100 %, se destaca como señal a revisar, no como confirmación de desbordamiento ni de que el Burguillo esté soltando agua. Consulta también el caudal de salida del Burguillo y la información oficial.

## Ejecutar

Se necesita Python 3.11 o posterior y las dependencias de `requirements.txt`. En Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Visita `http://localhost:8501`. Para detenerlo, pulsa `Ctrl+C`. Al reiniciar la aplicación se descartan los datos y se vuelven a consultar al abrirla.

## Streamlit Community Cloud

Sube el proyecto a un repositorio de GitHub, conecta el repositorio en [Streamlit Community Cloud](https://streamlit.io/cloud) y selecciona `app.py` como archivo principal. Community Cloud instalará las dependencias de `requirements.txt`. No se necesita una base de datos ni un volumen persistente. Comprueba que el servicio pueda acceder a los endpoints del SAIH desde la nube.

## Servidor con Docker

En un servidor con Docker instalado, desde la carpeta del proyecto:

```sh
docker build -t burguillo-monitor .
docker run -d --name burguillo --restart unless-stopped -p 127.0.0.1:8080:8080 burguillo-monitor
```

Consulta los errores con `docker logs burguillo`. Los datos se conservan solo en memoria y se vuelven a consultar al abrir la aplicación después de reiniciar el contenedor.

Para acceso externo, coloca el servicio tras un proxy inverso con HTTPS y controles de acceso adecuados. La aplicación no incorpora autenticación ni está diseñada para exponerse directamente a Internet.

## Datos y limitaciones

La aplicación consulta los endpoints que utiliza la web del SAIH para las cuatro estaciones. Son interfaces internas y podrían cambiar sin previo aviso. Se muestra la última lectura y la última consulta de cada estación; un error se muestra en pantalla y se registra, sin impedir la actualización de las demás. Las mediciones son automáticas y podrían no estar validadas. El acceso a los datos y su uso están sujetos a las condiciones de la fuente.

La respuesta observada contiene mediciones horarias recientes, aproximadamente de las últimas 24 horas. La aplicación muestra esas mediciones en memoria y reemplaza la captura de cada estación al actualizarla; no crea ni mantiene un histórico local. El gráfico no une puntos separados por más de 90 minutos.

Las fechas de medición se muestran exactamente como las proporciona el SAIH, sin información de zona horaria. La fuente puede publicar horas locales ambiguas en el cambio de hora; dos registros con la misma hora textual no pueden distinguirse por su fecha. La última consulta se muestra en la zona horaria del navegador.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
