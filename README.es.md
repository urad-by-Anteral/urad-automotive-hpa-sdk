# uRAD Automotive HPA SDK

**SDK oficial del radar Automotive HPA de [uRAD](https://urad.es) (Anteral)** —
placa de evaluación mmWave de 77 GHz basada en el **AWR1843** de Texas
Instruments (ISK, antena de altas prestaciones).

*Read this in [English](README.md).*

## Estructura del repositorio

| Directorio | Contenido |
|---|---|
| [`docs/`](docs) | Manual de usuario y guía del adaptador para Raspberry Pi (EN/ES) |
| [`mechanical/`](mechanical) | Modelo 3D de la placa (STEP) |
| [`firmware/`](firmware) | Guía de flasheo; los binarios están en [Releases](../../releases) |
| [`applications/`](applications) | Aplicaciones del producto (short range radar) |

## Inicio rápido (demo out-of-box)

1. Flashea el firmware out-of-box (`out_of_box_1843_isk.bin`, en
   [Releases](../../releases)) — véase [`firmware/README.md`](firmware/README.md).
2. Instala el SDK Python [urad-mmwave](https://github.com/<org>/urad-mmwave-core):

   ```bash
   pip install git+https://github.com/<org>/urad-mmwave-core.git
   ```

3. Ejecuta la demo con el perfil de este producto (identifica antes tus
   puertos COM):

   ```bash
   urad-mmwave --config profiles/automotive-hpa/config_radar.json --data-port COM7 --control-port COM8
   ```

   Añade `--gui` para el visor de nube de puntos en tiempo real. La
   referencia completa de configuración está en el README de
   [urad-mmwave-core](https://github.com/<org>/urad-mmwave-core).

## Aplicaciones

### Short Range Radar

Detección de objetos por zonas con GUI de escritorio (incluye grabación y
reproducción). Funciona sobre el mismo firmware out-of-box. Véase
[`applications/short_range_radar/`](applications/short_range_radar).

## Recursos de Texas Instruments

La documentación de TI que antes acompañaba a este SDK está disponible en TI:
la guía del [mmWave SDK](https://www.ti.com/tool/MMWAVE-SDK) y el
[TI Resource Explorer](https://dev.ti.com/tir/).

## Licencia

El código y la documentación de Anteral se publican bajo licencia
[MIT](LICENSE). El firmware y la documentación de Texas Instruments siguen
sujetos a sus respectivas licencias de TI.
