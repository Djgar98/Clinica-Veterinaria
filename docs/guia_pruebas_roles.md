# Guia de pruebas por roles (no tecnico)

Esta guia permite que cualquier persona pruebe el sistema completo sin conocimiento tecnico.

## 1) Objetivo

Validar que cada rol vea solo lo que corresponde y que los flujos clave funcionen:
- Citas
- Consultas y expediente
- Solicitudes y reprogramaciones
- Inventario y ventas
- Usuarios y auditoria (solo admin)

## 2) Roles del sistema

Roles disponibles:
- `ADMIN`
- `ASISTENTE`
- `VETERINARIO`
- `INVENTARIO`
- `DUENO`

Regla importante:
- Si un usuario tiene varios roles, el sistema usa el rol de mayor privilegio.
- Prioridad actual: `ADMIN` > `VETERINARIO` > `ASISTENTE` > `INVENTARIO` > `DUENO`.

## 3) Preparacion rapida del ambiente

1. Levantar servidor (recomendado para websocket/notificaciones):

```powershell
cd C:\Users\Danny Garcia\OneDrive\Documentos\Monografa\Proyecto\Clinica-Veterinaria
..\env\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 config_veterinaria.asgi:application
```

2. Entrar como admin y crear usuarios de prueba en:
- `http://127.0.0.1:8000/usuarios/nuevo/`

3. Crear al menos 1 usuario por rol:
- `admin.demo`
- `asistente.demo`
- `veterinario.demo`
- `inventario.demo`
- `dueno.demo`

4. Crear datos base:
- 2 mascotas (de distintos duenos)
- 3 productos de inventario
- 1 cita por confirmar
- 1 cita confirmada
- 1 solicitud de cita

## 4) Casos de prueba por rol

## 4.1 DUENO

Debe poder:
- Ver solo sus mascotas y sus citas.
- Crear solicitud de cita.
- Ver detalle de cita y estado.
- Confirmar cita solo cuando aplique en su flujo definido.

No debe poder:
- Editar ficha de mascota desde expediente.
- Aprobar/rechazar reprogramaciones.
- Administrar usuarios/roles.

Checklist:
- [ ] No ve mascotas de otros duenos.
- [ ] No aparece boton "Editar ficha" en expediente.
- [ ] Puede crear solicitud de cita.

## 4.2 VETERINARIO

Debe poder:
- Ver citas asignadas.
- Reprogramar cuando el estado lo permite.
- Abrir consulta solo cuando corresponde (no en por confirmar).
- Registrar consulta en expediente.
- Editar mascota (incluida fecha) segun permisos aplicados.

No debe poder:
- Gestionar usuarios.
- Ejecutar funciones administrativas de sistema.

Checklist:
- [ ] Ve solo su agenda asignada.
- [ ] Puede registrar consulta y ver historial.
- [ ] Puede editar mascota desde ruta de edicion.

## 4.3 ASISTENTE

Debe poder:
- Crear y confirmar citas.
- Aprobar/rechazar solicitudes de reprogramacion.
- Gestionar solicitudes de cita.
- Aceptar/rechazar receta segun flujo.

No debe poder:
- Administrar roles de usuarios.

Checklist:
- [ ] Puede pasar cita de por confirmar a confirmada.
- [ ] Puede gestionar solicitudes/reprogramaciones.

## 4.4 INVENTARIO

Debe poder:
- Crear productos.
- Editar productos (con restricciones de campos definidas).
- Gestionar lotes, movimientos y kardex.
- Crear ventas.

Restriccion esperada:
- Campos sensibles de costo/precio base bloqueados en editar (si asi esta definido).

Checklist:
- [ ] Puede crear producto con campos requeridos.
- [ ] En editar, respeta restricciones de campos sensibles.
- [ ] Kardex muestra informacion de autorizacion en ajustes.

## 4.5 ADMIN

Debe poder todo:
- Usuarios, roles, auditoria, accesos.
- Citas, consultas, solicitudes, inventario.
- Configuracion global.

Checklist:
- [ ] Acceso completo sin errores de permisos.
- [ ] Vista de auditoria y accesos disponible.

## 5) Flujo completo recomendado (demo de punta a punta)

1. `DUENO` crea solicitud de cita.
2. `ASISTENTE` aprueba y agenda.
3. `DUENO` confirma (si aplica en tu regla activa).
4. `VETERINARIO` atiende y registra consulta.
5. `VETERINARIO` genera receta.
6. `ASISTENTE` acepta receta y se genera venta.
7. `INVENTARIO` valida salida en kardex y stock.
8. `ADMIN` valida auditoria del proceso.

Resultado esperado:
- Trazabilidad completa de evento a evento.

## 6) Matriz de evidencia para testers

Para cada caso, pedir 3 cosas:
- Captura de pantalla
- URL visitada
- Resultado: `OK` o `Falla` + breve descripcion

Plantilla:
- Caso:
- Usuario/Rol:
- URL:
- Pasos:
- Resultado esperado:
- Resultado real:
- Evidencia:

## 7) Pruebas remotas (personas a distancia)

Si es prueba temporal:
- Publicar local con Cloudflare Tunnel.
- Agregar host dinamico en `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
- Compartir URL HTTPS y credenciales de prueba por rol.

## 8) Criterio de salida (aceptacion)

Se considera listo para despliegue de prueba cuando:
- [ ] No hay errores 500/403 de host/csrf.
- [ ] Notificaciones en tiempo real funcionan con Daphne.
- [ ] Flujos por rol cumplen la matriz.
- [ ] No hay texto corrupto visible (encoding).
- [ ] Auditoria registra acciones criticas.
