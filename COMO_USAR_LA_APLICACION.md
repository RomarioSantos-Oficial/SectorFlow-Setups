# Como Usar la Aplicacion

Esta guia explica el paso a paso para usar Sector Flow Setups como usuario.

## 1. Que Hace la Aplicacion

La aplicacion ayuda a:

1. leer la telemetria de Le Mans Ultimate en tiempo real;
2. entender el comportamiento del coche;
3. recibir sugerencias de setup con heuristicas e IA;
4. crear un nuevo archivo .svm sin modificar el archivo base;
5. mejorar con el tiempo usando tus vueltas.

## 2. Antes de Empezar

Comprueba esto:

1. estas en Windows;
2. Python y dependencias estan instalados;
3. Le Mans Ultimate esta instalado;
4. Shared Memory funciona;
5. tienes al menos un archivo .svm para usar como setup base.

Instalacion:

```bash
pip install -r requirements.txt
python main.py
```

## 3. Paso a Paso

### Paso 1. Abrir la aplicacion

Ejecuta:

```bash
python main.py
```

### Paso 2. Esperar la conexion con el juego

La parte superior muestra indicadores para LMU, IA y base de datos.

### Paso 3. Cargar un setup base

En la pestana Setup:

1. haz clic en Load .svm;
2. selecciona un archivo;
3. espera la confirmacion.

### Paso 4. Salir a pista

Conduce algunas vueltas para que la aplicacion recopile telemetria.

### Paso 5. Revisar la telemetria

En la pestana Telemetria puedes ver tiempos, neumaticos, combustible, clima y frenos.

### Paso 6. Pedir una sugerencia

Puedes hacerlo de tres formas:

1. escribiendo en el chat de Setup;
2. usando el boton de sugerencia IA;
3. usando el boton de heuristicas.

Ejemplos:

- el coche tiene subviraje en la entrada;
- necesito setup para lluvia;
- rear wing +2;
- tc map -1.

### Paso 7. Revisar las sugerencias

Las sugerencias aparecen en el panel derecho de Setup con deltas y advertencias.

### Paso 8. Enviar feedback detallado

Usa la pestana Feedback para describir subviraje, sobreviraje, frenada, traccion, rigidez y desgaste.

### Paso 9. Crear un nuevo setup

1. haz clic en Create Setup;
2. elige el modo;
3. elige el clima;
4. confirma.

### Paso 10. Editar un setup existente

1. haz clic en Edit Setup;
2. selecciona el archivo .svm;
3. confirma el backup;
4. pide una sugerencia;
5. aplica los ajustes.

## 4. Soporte de Idiomas

Es posible mostrar la aplicacion en ingles, espanol, japones y chino, pero hoy la interfaz sigue con textos fijos en portugues.

Para hacerlo bien, hace falta:

1. centralizar textos de interfaz;
2. crear archivos de traduccion;
3. agregar selector de idioma;
4. cargar etiquetas y mensajes segun el idioma elegido.