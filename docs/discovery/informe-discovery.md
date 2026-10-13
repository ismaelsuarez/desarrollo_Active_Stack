# Informe de Discovery

## Sistema de gestión de turnos y agenda de pacientes para consultorios odontológicos

| | |
|---|---|
| **Materia** | Metodología I |
| **Carrera** | Tecnicatura Universitaria en Programación, UTN |
| **Trabajo** | Trabajo de Integración: del Discovery al primer Change, con Spec-Driven Development y Active Stack |
| **Integrantes** | Avalos, Pablo · Blangetti, Sofia · Suarez, Ismael |
| **Fecha del informe** | 2026-10-12 |
| **Fecha de consulta de las fuentes** | 2026-10-02 (relevamiento) y 2026-10-12 (verificación) |

---

## Resumen ejecutivo

**Qué se investigó.** Se relevaron 24 sistemas odontológicos que gestionan turnos y agenda de pacientes: 7 con dominio o presencia en Argentina, 9 del resto de Latinoamérica y España, y 8 internacionales, más 2 productos complementarios que no se puntuaron. El relevamiento se hizo solo sobre fuentes públicas (sitios oficiales, páginas de precios, centros de ayuda, documentación técnica y fichas de terceros), consultadas el 2026-10-02. El 2026-10-12 se volvieron a abrir las fuentes de 12 de esos sistemas y de un complemento y se corrigió lo que no tenía respaldo. No se accedió a demos, aplicaciones ni videos, y no se contactó a ningún proveedor.

**Principales hallazgos.**

1. **Ningún sistema relevado documenta la prevención de solapamientos.** Tampoco se documentan reglas para los sobreturnos: Dentalink ofrece el sobreagendamiento como una opción al agendar, sin límites ni autorización.
2. **La evidencia de los proveedores argentinos es mayormente comercial.** La excepción es Bilog, cuyo centro de ayuda documenta los recordatorios y la liquidación de obras sociales. Los proveedores de Brasil, Chile y el exterior documentan más, lo que los hace más verificables, no necesariamente mejores.
3. **La autogestión del paciente es parcial en Argentina.** Bilog y AgendaPro declaran que el paciente toma y cancela turnos; DentalCore solo permite confirmar o cancelar un turno ya cargado. La reprogramación por el paciente y la lista de espera no se evidencian en ningún proveedor local.
4. **Ningún sistema supera 3,75 sobre 5.** El puntaje más alto es el de DentalCore, que se apoya en afirmaciones comerciales de un proveedor sin reseñas. Las diferencias de 0,05 a 0,20 entre los sistemas intermedios están dentro del error de estimación.
5. **Los precios son desparejos.** AgendaPro, Odonthia y DentalCore publican valores; DentalTec, Bilog, Hessy y OdontoGRAMA no publican importes.
6. **Los productos están partidos.** Quien es fuerte en obras sociales (DentalTec) es débil en experiencia del paciente, y quien es fuerte en reserva online (AgendaPro) es débil en clínica y obras sociales.

**MVP recomendado.** Un producto centrado en el turno, para consultorios de 2 a 5 profesionales: agenda por profesional con duración según la prestación, prevención de solapamientos garantizada, sobreturnos solo con autorización, reserva online por enlace público con confirmación, cancelación y reprogramación por el paciente, recordatorios automáticos y un indicador de ausentismo. La facturación con ARCA, las obras sociales y la gestión clínica (odontograma, presupuestos) quedan para etapas posteriores. El detalle está en la [sección D](#d-recomendación-final).

**Qué cambió con la verificación.** De las afirmaciones revisadas el 2026-10-12, las que más pesaban no tenían respaldo: la prevención de solapamientos de Clinicorp, la autogestión del paciente de DentalCore y la falta de documentación de ayuda en todos los proveedores argentinos. El detalle está en la sección [Verificación de fuentes](#verificación-de-fuentes).

---

## Cómo leer este informe

- **[C] Comprobado**: la función figura en documentación pública, centro de ayuda, tarifa publicada o ficha de terceros verificable.
- **[AC] Afirmación comercial**: la función figura solo en material de marketing del proveedor. No se verificó en uso.
- **No evidenciado**: el dato no apareció en las páginas consultadas o no quedó registrado en el relevamiento. No implica que la función no exista.

Las cifras de adopción (clientes, profesionales, años en el mercado) son las que declara cada proveedor, salvo que se indique otra cosa.

---

## A. Tabla comparativa

24 sistemas, ordenados por relevancia para Argentina. Criterio de orden: presencia o localización argentina evidenciada, cobertura de agenda y turnos, y disponibilidad de información verificable. La última columna indica la fecha de la última consulta de cada fila: las de 2026-10-12 se volvieron a abrir en la verificación; las de 2026-10-02 conservan el dato del relevamiento.

| # | Producto / Proveedor | País · Segmento · Modalidad | Agenda y turnos digitales | Gestión odontológica | Administración e integraciones locales | Modelo comercial y adopción | Fuente y fecha |
|---|---|---|---|---|---|---|---|
| 1 | **DentalCore** / Alfredo Di Tullio | Argentina (La Plata) · Consultorio y clínica pequeña · Web, Android, iOS | Agenda multi-doctor y multi-clínica; recordatorios por WhatsApp con 5 tipos de mensajes automáticos, apagados por defecto; el paciente confirma o cancela por enlace un turno ya cargado [AC]. Reserva por el paciente: No evidenciado (el portal del paciente figura como "próximamente"). Google Calendar: No evidenciado. Asignación de box o sillón: No evidenciado. Sobreturnos: No evidenciado | Historia clínica, odontograma, periodontograma, un módulo por especialidad, recetas, consentimientos y derivaciones [AC] | Facturación electrónica de ARCA con CAE y QR; obras sociales y prepagas, con OSDE, Swiss Medical y PAMI precargadas; cobros con Mercado Pago por QR o enlace; exportación en HL7 FHIR; roles y permisos por persona [AC] | Plan único de USD 50/mes con 2 usuarios y USD 10 por usuario adicional [C]. La ficha de Capterra indica USD 49 por mes, prueba gratuita y versión gratuita, que el sitio oficial no menciona [C]. 0 reseñas en Capterra. El soporte lo da el fundador | dentalcore.app, dentalcore.app/pricing y capterra.com/p/10047210/Dentalcore · 2026-10-12 |
| 2 | **DentalTec** / Tándem (razón social: No evidenciado) | Argentina (San Juan) · Odontólogos, círculos, federaciones y obras sociales · Nube | Agenda por profesional con recordatorios automáticos por WhatsApp; el paciente confirma por WhatsApp [AC]. Reserva online por el paciente: No evidenciado | Odontograma con CIE-10; imágenes como adjuntos del historial [AC] | Validación de prácticas contra obras sociales en línea, más de 15 obras sociales, facturación electrónica con ARCA, liquidaciones [AC] | Precio del sistema: No evidenciado. Paquetes de WhatsApp de USD 9, 25 y 48 [C]. Adopción: No evidenciado | web.dentaltec.com.ar/funcionalidades y web.dentaltec.com.ar/preguntas-frecuentes · 2026-10-12 |
| 3 | **Odonthia** / Genera Impacto | Argentina · Odontólogo independiente y consultorio · Nube | Reserva online mencionada sin detalle; WhatsApp automático incluido en los planes pagos [AC]. Multi-box: No evidenciado. Lista de espera: No evidenciado | Odontograma FDI, periodontograma, ortodoncia, presupuestos, consentimientos firmados desde el celular [AC] | Obras sociales y prepagas: módulo mencionado sin detalle [AC]. ARCA: No evidenciado. Mercado Pago: solo como medio de cobro de la suscripción. Declara que le alcanza la Ley 25.326 y cita la Ley 26.529 | Plan gratuito. En Argentina, ARS 20.900 (Odonthia IA) y ARS 46.900 (Odonthia Max) por mes; fuera de Argentina, USD 26 y USD 44 [C]. Adopción: No evidenciado | odonthia.com/planes y odonthia.com/privacidad · 2026-10-12 |
| 4 | **Bilog** / Bilog Soluciones Informáticas (nombre comercial) | Argentina (Buenos Aires) · Clínicas y consultorios · SaaS con aplicaciones | Turnos online: los pacientes toman y cancelan turnos, como pack de los planes Lite y Premium; QR de alta rápida de pacientes [AC]. Recordatorios por WhatsApp, SMS, correo o llamada [C, en la ayuda]. Reprogramación por el paciente: No evidenciado | Historia clínica, odontograma, presupuestos, galería de imágenes, recetas electrónicas [AC] | Liquidación de obras sociales [C, en la ayuda]. Prepagas: No evidenciado. ARCA y Mercado Pago: No evidenciado | Plan Freemium sin costo, con 1 profesional y 1 usuario; Lite y Premium se cotizan por usuario, sin valores publicados [C]. Más de 20 años y más de 1.500 clínicas, cifras propias | bilog.com.ar/planes y docs.bilog.com.ar · 2026-10-12 |
| 5 | **AgendaPro** / AgendaPro SpA | Chile, con sitio y precios para Argentina · Plataforma horizontal con vertical dental · Nube y aplicaciones | Reserva 24/7 sin registro, seña al reservar, recordatorios por WhatsApp, SMS o correo, doble confirmación, turnos por práctica y por profesional [AC] | Ficha dental editable; odontograma solo como adjunto [AC, consulta del 2026-10-02] | Pagos en línea, sin nombrar el medio [AC]. Mercado Pago: No evidenciado. Facturación electrónica: figura como "próximamente". ARCA y obras sociales: No evidenciado | ARS 13.900, 33.900 y 44.900 por mes, y plan Pro de ARS 314.900, con IVA incluido [C]. Más de 135.000 profesionales, cifra propia y global | agendapro.com/ar/planes, agendapro.com/ar/dental/software-odontologico y agendapro.com/ar/terminos-y-condiciones · 2026-10-12 |
| 6 | **Dentalink** / Healthatom | Chile, con página para Argentina · Clínicas y consultorios · Nube | Vistas diaria, semanal y diaria global, profesional más sillón, bloqueos programados y horarios especiales [C, en la ayuda]. Sobreagendamiento como opción al agendar, sin reglas ni límites documentados [C, en la ayuda]. Notificación de citas por WhatsApp [C, en la ayuda]. Agendamiento online [AC], no localizado en la ayuda | Odontograma, periodontograma, presupuestos, consentimientos, ortodoncia, IA [AC, consulta del 2026-10-02] | Enlace a un módulo de obras sociales en la página argentina, sin detalle verificado [AC]. ARCA: No evidenciado | Precio en el sitio: No evidenciado. Capterra: desde USD 29 por usuario. Adopción: No evidenciado | softwaredentalink.com/ar e intercom.help/softwaredentalink/es · 2026-10-12 |
| 7 | **Doctocliq** / Proveedor: No evidenciado | Perú · Consultorios · Nube | Vistas por día, semana, mes, box y profesional, Google Calendar, enlace de reserva por WhatsApp, Instagram y Google, recordatorios en paquetes [AC] | Odontograma, periodontograma, presupuestos con seguimiento, receta digital [AC] | Facturación electrónica solo en Perú, México, Ecuador y Colombia. ARCA: No evidenciado | Plan gratuito de 30 citas por mes; plan individual desde USD 19 [C]. Adopción: No evidenciado | doctocliq.com · 2026-10-02 |
| 8 | **Odeen** / Proveedor: No evidenciado | Chile · Consultorios pequeños · Nube | Reserva 24/7 y recordatorios por WhatsApp [AC] | Odontograma por superficie, periodontograma, presupuestos, consentimientos [AC] | Cobro online del paciente [AC]. Facturación local: No evidenciado | CLP 19.990 a 49.990 con IVA, asistentes sin costo [C]. Producto nuevo, sin reseñas | odeen.cl · 2026-10-02 |
| 9 | **Simples Dental** / Proveedor: No evidenciado | Brasil · Consultorios y clínicas · Nube y aplicaciones | Vista por sillones, lista de espera y encaje [C, en la ayuda]. Enlace público y confirmación por WhatsApp y SMS [C]. Secretaria con IA por WhatsApp, de pago [AC] | Prontuario, odontograma, presupuestos, firma electrónica [C, en los planes]. Periodontograma: No evidenciado | Caja, Pix, boleto y factura de servicio, solo para Brasil. Integraciones argentinas: No evidenciado | BRL 137 a 321 por mes [C]. Adopción: No evidenciado | simplesdental.com y ajuda.simplesdental.com · 2026-10-02 |
| 10 | **Clinicorp** / Proveedor: No evidenciado | Brasil · Consultorios y clínicas con especialidades · Modalidad: No evidenciado | Agendamiento online, confirmación automática por WhatsApp, reagendamiento y cancelación mediante agentes de IA, reportes de faltas, cancelaciones y ocupación [AC]. Prevención de solapamiento: No evidenciado. Reserva por enlace: No evidenciado | Odontograma: No evidenciado. Fichas por especialidad [AC, consulta del 2026-10-02] | Solo para Brasil. Integraciones argentinas: No evidenciado | Plan Standard: BRL 159,90 en la página de planes y BRL 149,90 en la portada; plan Premium: BRL 369,90 [C]. Demostración gratuita, sin prueba autogestionada. Adopción: No evidenciado | clinicorp.com y clinicorp.com/planos · 2026-10-12 |
| 11 | **Dentidesk** / Proveedor: No evidenciado | Chile · Clínicas y universidades · Web y aplicaciones | Widget de reserva documentado con validación por RUT, correo de confirmación 24 h antes [C]. WhatsApp automático figura como próximo | Odontograma con tres nomenclaturas, fichas por especialidad, presupuestos, consentimientos [C] | Liquidación de profesionales, morosos, facturación SII de Chile [C]. Integraciones argentinas: No evidenciado | Precio: No evidenciado. Prueba de 15 días [C]. Adopción: No evidenciado | dentidesk.com · 2026-10-02 |
| 12 | **Odontosys** / Proveedor: No evidenciado | Uruguay, probable · Consultorios y clínicas · Web y aplicaciones | Agenda con confirmaciones por WhatsApp y correo [AC] | Odontograma, periodontograma, radiografías, presupuestos [AC] | Planes de pago y reportes [AC]. Integraciones argentinas: No evidenciado | Precio por cantidad de dispositivos, sin valores publicados; sin prueba. Certificaciones ISO y SOC declaradas, sin informes | odontosys.com · 2026-10-02 |
| 13 | **OdontoGRAMA** / Julio Santolo · Solsoftware | Argentina (San Luis) · Consultorio · Nube | Agendas de turnos personalizables, con control de asistencia [AC]. Turnos online y recordatorios: No evidenciado | Imágenes, tratamientos, diagnósticos y motivos de consulta [AC] | Facturación a prepagas y obras sociales, caja, cuentas corrientes [AC] | Precio: No evidenciado (la página devuelve error 500). Acceso gratuito a todas las funciones, según la portada. Adopción: No evidenciado | odontograma.com.ar y solsoftware.com.ar · 2026-10-12 |
| 14 | **Hessy** / Proveedor: No evidenciado | País: No evidenciado (teléfono con prefijo argentino +54 9 341) · Consultorio · Nube | Agenda de varios profesionales a la vez [AC]. Reserva online y recordatorios: No evidenciado | Odontograma 3D, hoja de evolución, presupuestos [AC] | Caja [AC]. Integraciones: No evidenciado | Página de precios sin importes. Prueba de 7 días. Adopción: No evidenciado | hessydental.com y hessydental.com/precios · 2026-10-12 |
| 15 | **OdontoApp** / Proveedor: No evidenciado | Latinoamérica (declara 19 países, con dominio .com.ar) · Odontólogo independiente y clínicas · Modalidad: No evidenciado | Calendario de turnos y recordatorios automáticos [AC] | Fichas clínicas, odontograma [AC] | No evidenciado | Precio: No evidenciado (`/precios` devuelve 404 y la sección de planes no muestra importes). Más de 100 odontólogos y clínicas, cifra propia | odontoapp.com.ar · 2026-10-12 |
| 16 | **Nubimed** / Proveedor: No evidenciado | España · Clínicas dentales · Modalidad: No evidenciado | Reserva online, Google Calendar [AC] | Odontograma, periodontograma, firma digital [AC] | Facturación e inventario [AC]. Presencia argentina: No evidenciado | Precio: No evidenciado. Adopción: No evidenciado | nubimed.com · 2026-10-02 |
| 17 | **Medesk** / Proveedor: No evidenciado | País de origen: No evidenciado · Clínicas · Nube | Cita online y mensajería automática [AC] | Odontograma, historia clínica [AC] | Facturación electrónica, roles [AC]. Presencia argentina: No evidenciado | Comienza gratis; calculadora de precios sin valores. Adopción: No evidenciado | medesk.net · 2026-10-02 |
| 18 | **Open Dental** / Proveedor: No evidenciado | EE. UU. · Consultorios de cualquier tamaño · Escritorio con servicios web | Web Sched, eConfirmations por texto o correo, lista ASAP [C, consulta del 2026-10-02] | Gráfico dental, imágenes [C, consulta del 2026-10-02]. Periodontograma: No evidenciado | Cientos de conectores (bridges). Facturación y pagos locales: No evidenciado | USD 89 por mes por sede en "otros países", con contrato de 12 meses y hasta 3 profesionales; gratis en países en desarrollo, con soporte limitado [C]. La página no indica en qué categoría entra Argentina | opendental.com/site/fees.html · 2026-10-12 |
| 19 | **Dentrix / Dentrix Ascend** / Henry Schein One | EE. UU. · Consultorios y grupos · Local y nube | Reserva online y recordatorios [AC] | Charting con IA [AC] | Formularios de paciente en español desde el 2025-07-23 [C]. Facturación local: No evidenciado | Precio: No evidenciado. Más de 35.000 prácticas, cifra propia | dentrix.com · 2026-10-02 |
| 20 | **Dentally** / Henry Schein One UK | Reino Unido · Clínicas y grupos multisitio · Nube | Portal de reserva, listas de espera, recordatorios y confirmaciones [C, consulta del 2026-10-02] | Charting y planes con IA [C, consulta del 2026-10-02] | API REST pública, con sandbox y endpoints por región (general, Asia-Pacífico y Canadá) [C]. Pagos del Reino Unido. Integraciones argentinas: No evidenciado | Precio en GBP por sillones [C, consulta del 2026-10-02]. Adopción: No evidenciado | dentally.com y developer.dentally.co · 2026-10-12 |
| 21 | **CareStack** / Proveedor: No evidenciado | EE. UU. · Grupos multiubicación · Nube | Reserva en línea, Reserve with Google, recordatorios [C] | Charting general y periodontal, imágenes con IA [C] | Pagos propios. SOC 2 e ISO 27001 declarados [AC]. Integraciones argentinas: No evidenciado | Precio: No evidenciado. Adopción: No evidenciado | carestack.com · 2026-10-02 |
| 22 | **Archy** / Proveedor: No evidenciado | EE. UU. · Consultorios · Nube | Reserva 24/7, recordatorios y recall con texto ilimitado [C] | Periodontograma por voz, IA [C] | Cobro por texto. Soporte local: No evidenciado | USD 899 por mes por sede [C]. Adopción: No evidenciado | archy.com · 2026-10-02 |
| 23 | **tab32** / Proveedor: No evidenciado | EE. UU. · Consultorios · Nube | Reserva fuera de horario, recordatorios por texto [C] | Charting, imagen con IA [C] | Soporte local: No evidenciado | Desde USD 125 por mes; prueba de 14 días [C]. Adopción: No evidenciado | tab32.com · 2026-10-02 |
| 24 | **Curve Dental** / Proveedor: No evidenciado | EE. UU. · Consultorios de EE. UU. y Canadá · Nube | Reserva online y recordatorios [C] | Módulo de periodontograma, imagen [C] | Curve Pay, membresías, solo para EE. UU. y Canadá. Integraciones argentinas: No evidenciado | Precio: No evidenciado. Adopción: No evidenciado | curvedental.com · 2026-10-02 |

**Complementos relevados, no puntuados**

- **YoFacturo** (Argentina, yo-facturo.com/clinicas, consultado el 2026-10-12): no es un sistema dental. Ofrece agenda de turnos por profesional, facturación A, B o C con CAE de ARCA, cuenta corriente por obra social y, como módulo aparte, cobros con Mercado Pago. Declara que no se integra con los sistemas de las obras sociales. Planes de ARS 20.000, 50.000, 75.000 y 150.000 por mes, más un plan a medida [C].
- **NexHealth** (EE. UU., nexhealth.com, consultado el 2026-10-02): capa de reserva, recall y lista de espera sobre un sistema existente. Sirve solo como referencia de experiencia.

**Buscados y no incluidos en la tabla**

- **Sin poder comprobar**: EIRA/Titaves (titaves.com.ar devolvió error 503 el 2026-10-12), BestoSys, Vitena, Clinic Cloud, Dendoo, DentalSoft Plus y Medilink.
- **Descartados por no operar en Argentina**: MR Dentalcloud (México) y DentalPin (España).
- **Sistemas de turnos genéricos, no odontológicos**: Gendu (gendu.com.ar, Argentina) y Turnito (turnito.app, Argentina). Ambos publican precios en pesos y reserva online; ninguno documenta prevención de solapamientos ni sobreturnos.

La búsqueda del 2026-10-12 no encontró ningún otro sistema odontológico argentino con página oficial verificable.

---

## B. Matriz de puntuación

**Pesos.** T = Gestión de turnos y automatización (25 %). C = Funcionalidad odontológica clínica (20 %). I = Integraciones locales y WhatsApp (15 %). A = Administración, cobros y facturación (15 %). E = Experiencia del paciente (10 %). S = Seguridad, exportación y trazabilidad (10 %). P = Precio y facilidad de adopción (5 %).

| Sistema | T | C | I | A | E | S | P | **Total** |
|---|---|---|---|---|---|---|---|---|
| DentalCore | 3 | 4 | 5 | 4 | 3 | 4 | 3 | **3,75** |
| Doctocliq | 4 | 4 | 2 | 2 | 3 | 2 | 5 | **3,15** |
| Odonthia | 3 | 4 | 2 | 2 | 3 | 4 | 5 | **3,10** |
| Simples Dental | 4 | 4 | 2 | 2 | 3 | 2 | 4 | **3,10** |
| Bilog | 4 | 3 | 2 | 3 | 4 | 1 | 3 | **3,00** |
| Dentalink | 3 | 4 | 2 | 3 | 3 | 2 | 3 | **2,95** |
| Odeen | 3 | 4 | 1 | 2 | 3 | 4 | 4 | **2,90** |
| AgendaPro | 4 | 2 | 2 | 3 | 4 | 1 | 4 | **2,85** |
| DentalTec | 3 | 2 | 4 | 4 | 1 | 2 | 2 | **2,75** |
| Dentidesk | 3 | 4 | 1 | 2 | 3 | 2 | 3 | **2,65** |
| CareStack | 3 | 4 | 1 | 2 | 3 | 3 | 1 | **2,65** |
| Archy | 4 | 4 | 0 | 2 | 3 | 2 | 1 | **2,65** |
| Clinicorp | 3 | 3 | 2 | 2 | 3 | 2 | 3 | **2,60** |
| Odontosys | 3 | 4 | 1 | 2 | 2 | 3 | 2 | **2,60** |
| Nubimed | 3 | 4 | 1 | 2 | 3 | 2 | 2 | **2,60** |
| Dentally | 3 | 3 | 2 | 1 | 3 | 3 | 3 | **2,55** |
| Medesk | 3 | 3 | 1 | 2 | 3 | 2 | 3 | **2,45** |
| Open Dental | 3 | 3 | 1 | 1 | 2 | 2 | 4 | **2,25** |
| Dentrix / Ascend | 3 | 3 | 1 | 1 | 2 | 3 | 2 | **2,25** |
| Curve Dental | 3 | 4 | 0 | 1 | 3 | 2 | 1 | **2,25** |
| tab32 | 3 | 3 | 0 | 1 | 3 | 2 | 3 | **2,15** |
| Hessy | 1 | 2 | 0 | 2 | 1 | 1 | 2 | **1,25** |
| OdontoGRAMA | 1 | 2 | 0 | 2 | 0 | 1 | 2 | **1,15** |
| OdontoApp | 1 | 1 | 0 | 0 | 1 | 0 | 1 | **0,60** |

### Notas modificadas tras la verificación del 2026-10-12

| Sistema | Cambio | Motivo | Total anterior | Total actual |
|---|---|---|---|---|
| DentalCore | T de 4 a 3; E de 4 a 3; S de 3 a 4 | El paciente no reserva, solo confirma o cancela; no hay bot con 9 automatizaciones ni Google Calendar. La página de precios declara exportación en HL7 FHIR y roles por persona | 4,00 | 3,75 |
| Bilog | T de 3 a 4; E de 3 a 4; P de 2 a 3 | Los pacientes toman y cancelan turnos; la ayuda documenta los recordatorios; existe un plan sin costo | 2,60 | 3,00 |
| AgendaPro | I de 3 a 2 | Mercado Pago no figura en las páginas consultadas | 3,00 | 2,85 |
| Clinicorp | T de 4 a 3; E de 4 a 3 | La prevención de solapamiento y la reserva por enlace no figuran; el reagendamiento es solo por agentes de IA | 2,95 | 2,60 |

### Nota metodológica

Los puntajes son una estimación del analista basada solo en evidencia pública. No son una medición en uso.

**Qué significa cada nota**

| Nota | Significado |
|---|---|
| 0 | No evidenciado |
| 1 | Mención mínima |
| 3 | Cobertura declarada razonable |
| 5 | Cobertura completa, evidenciada y adaptada a Argentina |

La escala no define las notas 2 y 4; se usaron como valores intermedios entre las anteriores.

**Cómo se trataron los datos "No evidenciado".** Un criterio sin ninguna evidencia pública vale 0. No se completó por deducción ni por similitud con productos parecidos. Por eso un puntaje bajo indica falta de evidencia, no necesariamente falta de la función.

**Cómo se trataron las afirmaciones comerciales.** Se puntuaron con prudencia: una función que solo figura en material de marketing suma, pero menos que una documentada.

**Sesgos conocidos**

- El criterio de integraciones locales penaliza por diseño a los sistemas extranjeros.
- Los pesos favorecen a quien comunica más funciones. Un proveedor con buena agenda y poca comunicación pública queda subestimado.
- El puntaje de DentalCore (3,75) refleja lo que el proveedor declara, no lo que está demostrado: no tiene reseñas y el soporte lo da el propio fundador.
- Solo se volvieron a puntuar los cuatro sistemas cuyas fuentes cambiaron de forma relevante en la verificación. Los demás conservan la nota del relevamiento.
- Las diferencias de 0,05 a 0,20 entre los sistemas intermedios están dentro del error de estimación y no justifican un ranking estricto.

---

## C. Análisis competitivo

### C.1 Funcionalidades que ya son estándar de mercado

Se declaran en casi todos los sistemas, aunque se documentan solo en una minoría:

- Agenda multi-profesional en la nube.
- Recordatorios automáticos por correo, SMS o WhatsApp.
- Historia clínica, odontograma y presupuestos.
- Reserva online del paciente.
- Roles de usuario.
- Demo o prueba gratuita.

La IA en radiografías y en notas por voz aparece en la mayoría de los productos nuevos y se está volviendo un estándar, no una ventaja.

### C.2 Funcionalidades diferenciadoras reales

Se encuentran en pocos productos:

| Funcionalidad | Quién la ofrece | Tipo de evidencia |
|---|---|---|
| Lista de espera o encaje de huecos | Simples Dental, Open Dental (lista ASAP), Dentally | Comprobado |
| Agenda por sillón, con bloqueos y horarios especiales | Dentalink | Comprobado |
| API pública con sandbox | Dentally | Comprobado |
| Toma y cancelación de turnos por el paciente | Bilog, AgendaPro | Afirmación comercial |
| Reportes de faltas, cancelaciones y ocupación | Clinicorp | Afirmación comercial |
| Seña o prepago al reservar | AgendaPro | Afirmación comercial |
| Validación de prácticas contra obras sociales en línea | DentalTec | Afirmación comercial |
| ARCA, obras sociales y Mercado Pago en un único producto | DentalCore | Afirmación comercial |
| Auditoría de accesos y doble factor | Odeen | Afirmación comercial |

Las tres primeras son las únicas respaldadas por documentación. Las restantes dependen de lo que declara cada proveedor.

**La prevención de solapamientos no figura en esta tabla porque ningún sistema relevado la documenta.** El relevamiento del 2026-10-02 se la atribuía a Clinicorp; la verificación no la encontró en su sitio. Dentalink documenta lo contrario: permite el sobreagendamiento como una opción al agendar.

### C.3 Vacíos frecuentes del mercado argentino

1. **Poca evidencia verificable.** Entre los proveedores argentinos, solo Bilog tiene un centro de ayuda público. El resto respalda sus funciones solo con material comercial.
2. **Agenda con reglas.** Sobreturnos con autorización, bloqueos y prevención de solapamiento no se documentan en ningún proveedor local. DentalCore declara agenda multi-doctor, sin asignación de box.
3. **Autogestión incompleta del paciente.** Bilog y AgendaPro declaran la toma y la cancelación de turnos. La reprogramación por el paciente y la lista de espera no se evidencian en ningún proveedor local.
4. **Precios desparejos.** AgendaPro, Odonthia y DentalCore publican valores; DentalTec, Bilog, Hessy y OdontoGRAMA no publican importes.
5. **WhatsApp.** Abundan los recordatorios. Un flujo bidireccional de reserva por WhatsApp no se evidencia en ningún proveedor local.
6. **Seguridad y datos personales.** Solo Odonthia declara que le alcanza la Ley 25.326. Backups, auditoría y exportación casi nunca se detallan; DentalCore declara exportación en HL7 FHIR.
7. **Obras sociales.** DentalTec, DentalCore, Bilog y OdontoGRAMA lo declaran. Solo Bilog documenta la liquidación en su ayuda.
8. **Productos partidos.** Quien es fuerte en obras sociales (DentalTec) es débil en experiencia del paciente. Quien es fuerte en reserva (AgendaPro) es débil en clínica y obras sociales.

Los vacíos 2 y 3 se apoyan en la ausencia de evidencia pública, no en una prueba de que la función falte. Una demo de los proveedores locales podría desmentirlos.

### C.4 Oportunidades de innovación

- **Agenda primero.** Un sistema donde el turno sea el centro, con multi-box, duración por prestación y prevención de solapamiento demostrable.
- **Autogestión completa por WhatsApp.** Reservar, confirmar, cancelar y reprogramar sin intervención de recepción.
- **Relleno automático de huecos** con lista de espera, para reducir el ausentismo.
- **Seña por Mercado Pago al reservar**, con política de cancelación configurable.
- **Métricas de ausentismo y ocupación** visibles para el consultorio.
- **Transparencia.** Precio publicado en pesos, exportación de datos y migración desde la competencia.
- **Cumplimiento verificable.** Registro de auditoría y consentimientos conforme a la Ley 25.326, con documentación pública.
- **Obras sociales y ARCA como segunda etapa**, no como requisito de entrada.

---

## D. Recomendación final

### D.1 Cinco competidores prioritarios para analizar mediante demo

Criterio: relevancia para Argentina y brecha de verificación.

| # | Competidor | Por qué | Qué verificar en la demo |
|---|---|---|---|
| 1 | DentalCore | Es el más completo en localización argentina declarada | ARCA, obras sociales y los mensajes de WhatsApp en pantalla; el estado del portal del paciente; la continuidad de un proveedor cuyo soporte da el fundador |
| 2 | DentalTec | Referente en obras sociales | Si existen turnos online para el paciente |
| 3 | Dentalink (página para Argentina) | Tiene la mejor documentación pública de agenda | La localización real y el flujo de WhatsApp |
| 4 | AgendaPro | Ya tiene sitio y precios para Argentina | La reserva con seña, el medio de pago que usa y sus límites clínicos |
| 5 | Odonthia | Plan gratuito y precios publicados en pesos | El alcance de la reserva online y del módulo de obras sociales |

### D.2 Tres productos de referencia para experiencia de usuario

1. **Simples Dental**: agenda por sillones, lista de espera y enlace público de reserva.
2. **Dentalink**: la agenda mejor documentada, con sillón, bloqueos y horarios especiales.
3. **AgendaPro**: reserva 24/7 sin registro, con seña.

Clinicorp figuraba en esta lista por la prevención de solapamiento y el reagendamiento automático. La verificación no encontró esas funciones en su sitio, así que se lo reemplazó por Dentalink. NexHealth sirve como referencia complementaria de lista de espera y recall.

### D.3 MVP sugerido

Producto centrado en turnos y agenda, para un consultorio de 2 a 5 profesionales. La propuesta inicial del 2026-10-02 se validó con el responsable del proyecto y se ajustó el 2026-10-05; las tres listas reflejan el alcance validado y los cambios figuran en [D.4](#d4-ajustes-respecto-de-la-propuesta-inicial).

**Imprescindibles**

1. Agenda por profesional, con un box fijo por profesional, duración según la prestación y bloqueos.
2. Horario semanal propio por profesional, con excepciones por fecha (feriados, vacaciones, ausencias) que bloquean la agenda.
3. Catálogo inicial editable de prestaciones comunes, con duraciones sugeridas.
4. Prevención de solapamientos, y sobreturnos solo con autorización.
5. Reserva online por enlace público, con confirmación, cancelación y reprogramación por el paciente.
6. Confirmación y recordatorios por correo automático, y por WhatsApp con un mensaje preparado por el sistema que recepción envía con un clic.
7. Estados del turno: pendiente, confirmado, ausente, atendido y cancelado.
8. Cinco roles con permisos: administrador, recepción, profesional, paciente y administrativo. Este último existe solo como rol con permisos en la primera versión.
9. Ficha mínima de paciente: nombre y apellido, teléfono, correo, DNI, obra social como dato y notas.
10. Indicador de ausentismo para el administrador.

**Diferenciadores**

1. Auditoría y consentimiento de datos conforme a la Ley 25.326. El aviso de privacidad y su aceptación en el registro ya forman parte de la primera versión.
2. Lista de espera con relleno automático de huecos por cancelación.
3. Seña o pago por Mercado Pago al reservar.
4. Recall automático de controles periódicos.
5. Conversación bidireccional por la API oficial de WhatsApp Business, con envío automático de confirmaciones.
6. Importación desde planilla o Google Calendar.

**Etapas posteriores**

1. Facturación con ARCA.
2. Cobro, validación y liquidación con obras sociales y prepagas; contratos y documentación (funciones del rol administrativo).
3. Odontograma y periodontograma completos, presupuestos y planes de tratamiento.
4. Imágenes y radiografías con IA.
5. Multisucursal avanzado.
6. API pública y firma digital.

**Por qué este recorte.** Los imprescindibles 4 y 5 atacan dos vacíos del mercado argentino (C.3, puntos 2 y 3) y coinciden con el problema del consultorio: ausencias, confirmación manual y sobreturnos sin control. El imprescindible 4 es el de mayor diferenciación: ningún sistema relevado documenta la prevención de solapamientos. La gestión clínica y la facturación son estándar de mercado y ya las cubren los competidores; entrar por ahí no diferencia al producto.

**Primera funcionalidad a construir.** "Crear un turno evitando solapamientos" pertenece al imprescindible 4. Es una funcionalidad acotada, con reglas de negocio verificables, y es la base sobre la que se apoyan la reserva online y los sobreturnos.

### D.4 Ajustes respecto de la propuesta inicial

| Punto de la propuesta del 2026-10-02 | Alcance validado | Motivo |
|---|---|---|
| Agenda multi-profesional y multi-box | Un box fijo por profesional | Con un box fijo, validar el solapamiento por profesional alcanza |
| Roles básicos: administrador, recepción y profesional | Cinco roles; se agregan paciente y administrativo | El paciente reserva, confirma, cancela y reprograma por su cuenta; el administrativo existe solo como rol con permisos hasta que lleguen sus funciones |
| Ficha mínima con anamnesis breve y notas | Ficha mínima con notas, sin anamnesis | La anamnesis no figura en la ficha validada |
| Auditoría, consentimiento y tratamiento de datos conforme a la Ley 25.326, como imprescindible | Pasa a diferenciadores, primero en prioridad. El 2026-10-12 se adelantaron a la primera versión el aviso de privacidad y su aceptación en el registro | El plazo no permite todo en la primera versión. Queda registrado como riesgo: la ley aplica desde que se guardan datos personales |
| Tablero de ausentismo y ocupación, como diferenciador | Indicador de ausentismo, como imprescindible | Medir las ausencias es parte del problema que el producto resuelve |
| Recordatorios y confirmación por WhatsApp y correo | Correo automático y WhatsApp semimanual | La API oficial de WhatsApp tiene costo por conversación y exige aprobación de plantillas |
| Exportación de datos, como imprescindible | Fuera del alcance validado de la primera versión | No se ubicó en ninguna de las listas posteriores; queda como punto a decidir |
| Precio publicado en pesos, como imprescindible | Fuera del alcance validado de la primera versión | No se ubicó en ninguna de las listas posteriores; queda como punto a decidir |

---

## Verificación de fuentes

Los integrantes abrieron las fuentes el 2026-10-12. Antes, un agente de IA releyó las mismas páginas y señaló qué afirmaciones no encontraba; esa relectura sirvió de guía, y lo que se registra abajo es lo comprobado en cada página.

Resultados posibles: Confirmado, Parcial, No encontrado o Falso.

### Las cinco fuentes de la consigna

| # | Tipo | Fuente y URL | Qué afirmaba el informe | Qué se encontró | Qué se corrigió |
|---|---|---|---|---|---|
| 1 | Sitio oficial | DentalCore · https://www.dentalcore.app/ y https://www.dentalcore.app/pricing | USD 50 por mes con 2 usuarios; `/precios` devuelve 404; autoagendamiento, bot de WhatsApp con 9 automatizaciones y Google Calendar; ARCA, 20 obras sociales precargadas y Mercado Pago | **Parcial.** Confirmado: el precio, más USD 10 por usuario adicional; ARCA y Mercado Pago. `/precios` da 404, pero la página de precios existe en `/pricing`. No respaldado: el paciente no reserva, solo confirma o cancela por enlace; el sitio lista 5 tipos de mensajes automáticos, no un bot con 9; Google Calendar no figura; nombra 3 obras sociales, no 20 | Fila 1 de la tabla A. En la matriz B, T y E bajan de 4 a 3 y S sube de 3 a 4. Se quitó la expresión "proveedor unipersonal", que era una inferencia |
| 2 | Página de precios | Open Dental · https://www.opendental.com/site/fees.html | USD 89 por mes por sede en "otros países"; gratis en países en desarrollo | **Confirmado.** La página agrega un contrato de 12 meses y un tope de 3 profesionales, y soporte limitado en el plan gratuito. No dice en qué categoría entra Argentina | Fila 18 de la tabla A: se agregaron las condiciones y la aclaración sobre Argentina |
| 3 | Centro de ayuda | Dentalink · https://intercom.help/softwaredentalink/es | La ayuda documenta vistas, profesional más recurso, sobreagendamiento, bloqueos y horarios especiales; la reserva online y WhatsApp figuran en el material comercial y la ayuda los contradice | **Parcial.** Confirmada la agenda. El sobreagendamiento existe solo como opción al agendar, sin reglas. Falso que WhatsApp falte en la ayuda: hay un artículo sobre notificar citas por WhatsApp | Fila 6 de la tabla A. Dentalink pasa a ser referente de experiencia de usuario en D.2 |
| 4 | Marketplace | DentalCore en Capterra · https://www.capterra.com/p/10047210/Dentalcore/ | La ficha tiene 0 reseñas; indica un precio distinto del sitio oficial | **Confirmado**, con una precisión. La ficha, actualizada el 2026-10-05, muestra 0 reseñas de usuarios y un precio inicial de USD 49 por mes, frente a USD 50 del sitio: una diferencia de USD 1. Indica además prueba gratuita y versión gratuita, que la página de precios del sitio oficial no menciona | Fila 1 de la tabla A: se reemplazó "contradicción" por los dos valores y se agregó la diferencia sobre la versión gratuita |
| 5 | Documentación técnica | Dentally · https://developer.dentally.co | API REST pública, con sandbox y endpoints regionales | **Confirmado.** Se lee sin iniciar sesión. Lista un entorno sandbox y endpoints general, de Asia-Pacífico y de Canadá | Fila 20 de la tabla A: se precisaron las regiones |

### Fuentes adicionales comprobadas

| Fuente y URL | Qué afirmaba el informe | Qué se encontró | Qué se corrigió |
|---|---|---|---|
| Clinicorp · https://www.clinicorp.com/ y https://www.clinicorp.com/planos | Prevención de solapamiento, reserva por enlace, reagendamiento y cancelación automáticos, reporte de ausencias; planes de BRL 159,90 y 369,90, sin prueba gratuita | **Parcial.** Confirmados el reporte de ausencias y el plan Premium. No encontradas la prevención de solapamiento ni la reserva por enlace. El reagendamiento es solo mediante agentes de IA. El plan Standard figura con dos precios en el mismo sitio | Fila 10 de la tabla A; C.2; D.2; T y E bajan de 4 a 3 en la matriz B |
| Bilog · https://bilog.com.ar/planes/ y https://docs.bilog.com.ar | Sin precio publicado (`/precios` devuelve 404); liquidación de obras sociales y prepagas; ningún proveedor argentino con documentación de ayuda | **Falso en parte.** La página de planes existe en `/planes/`: plan Freemium sin costo, y Lite y Premium cotizados por usuario. Los pacientes toman y cancelan turnos. El centro de ayuda documenta los recordatorios y la liquidación de obras sociales. "Prepagas" no figura | Fila 4 de la tabla A; hallazgos 2 y 3 del resumen; vacíos 1, 3 y 7 de C.3; T, E y P suben en la matriz B |
| AgendaPro · https://agendapro.com/ar/planes | Precios solo en pesos chilenos; Mercado Pago; origen chileno sin confirmar | **Falso en parte.** Publica precios en pesos argentinos con IVA. Mercado Pago no figura. Los términos y condiciones nombran a AgendaPro SpA, bajo ley de Chile | Fila 5 de la tabla A; I baja de 3 a 2 en la matriz B |
| Odonthia · https://odonthia.com/planes y https://odonthia.com/privacidad | Complementos desde USD 26; el blog menciona ARS 20.900 a 46.900 (discrepancia de moneda); declara las Leyes 25.326, 26.529 y 25.506 | **Parcial.** Los valores en pesos están en la página de planes y son el precio para Argentina; los valores en dólares son para el exterior. No hay discrepancia. La Ley 25.506 aparece solo en un artículo del blog | Fila 3 de la tabla A; vacíos 4 y 6 de C.3 |
| DentalTec · https://web.dentaltec.com.ar/funcionalidades | Proveedor Tándem Digital; odontograma con CIE-10 e imágenes; más de 15 convenios | **Confirmado**, con una precisión: el sitio dice "Tándem"; la razón social no figura | Fila 2 de la tabla A |
| OdontoGRAMA · https://odontograma.com.ar | Proveedor Solsoftware | **Parcial.** El pie nombra a Julio Santolo; Solsoftware, de San Luis, lo lista como producto propio | Fila 13 de la tabla A |
| Hessy · https://hessydental.com | Argentina (Rosario) | **No encontrado.** El sitio no declara ciudad ni país; "Rosario" se había deducido del prefijo telefónico | Fila 14 de la tabla A |
| OdontoApp · https://odontoapp.com.ar/ | Unos 10 usuarios declarados | **Falso.** Declara más de 100 odontólogos y clínicas, en 19 países | Fila 15 de la tabla A |
| YoFacturo · https://yo-facturo.com/clinicas | Planes de ARS 20.000 a 150.000; no se integra con las obras sociales | **Confirmado.** Hay además un plan a medida | Lista de complementos |

### Qué enseñó la verificación

- **Las afirmaciones más útiles para el análisis eran las menos respaldadas.** La prevención de solapamientos de Clinicorp y la autogestión de DentalCore sostenían conclusiones de las secciones C y D, y ninguna figuraba en la fuente.
- **Un error 404 no prueba que el dato falte.** DentalCore y Bilog tienen página de precios, en `/pricing` y `/planes/`; el relevamiento probó solo `/precios`.
- **Un dato ausente de la portada puede estar en otra página.** Los precios en pesos de AgendaPro y de Odonthia estaban en sus páginas de planes.
- **Una deducción se había registrado como dato.** La ciudad de Hessy y el carácter unipersonal de DentalCore no estaban publicados.

---

## Limitaciones del relevamiento

- Las funciones se leyeron en páginas comerciales mediante extractores automáticos, que pueden omitir contenido o atribuir mal un dato, como el país de origen de AgendaPro.
- Ninguna funcionalidad se contrastó en uso real.
- La verificación del 2026-10-12 cubrió 12 de los 24 sistemas. Las filas con fecha 2026-10-02 no se volvieron a abrir.
- Precios y planes cambian. Los valores corresponden a la fecha de consulta.
- Las reseñas y las cifras de adopción provienen de Capterra y de cada proveedor. No están auditadas.
- Las comparativas de "mejores software" en Argentina las publican proveedores competidores o sitios de captación. Se usaron para descubrir candidatos, no como evidencia.

---

## Referencias

La columna de fecha indica la última consulta.

### Argentina

| Sistema | Fuente | Tipo | Fecha |
|---|---|---|---|
| DentalCore | https://www.dentalcore.app/ | Sitio oficial | 2026-10-12 |
| DentalCore | https://www.dentalcore.app/pricing | Página de precios | 2026-10-12 |
| DentalCore | https://www.capterra.com/p/10047210/Dentalcore/ | Marketplace | 2026-10-12 |
| DentalTec | https://web.dentaltec.com.ar/funcionalidades | Sitio oficial | 2026-10-12 |
| DentalTec | https://web.dentaltec.com.ar/preguntas-frecuentes | Sitio oficial | 2026-10-12 |
| Odonthia | https://odonthia.com/planes | Página de precios | 2026-10-12 |
| Odonthia | https://odonthia.com/privacidad | Política de privacidad | 2026-10-12 |
| Bilog | https://bilog.com.ar/planes/ | Página de planes | 2026-10-12 |
| Bilog | https://docs.bilog.com.ar/schedule/reminders | Centro de ayuda | 2026-10-12 |
| Bilog | https://docs.bilog.com.ar/liquidations/liquidations-coverage-medical | Centro de ayuda | 2026-10-12 |
| OdontoGRAMA | https://odontograma.com.ar | Sitio oficial | 2026-10-12 |
| OdontoGRAMA | https://solsoftware.com.ar | Sitio del proveedor | 2026-10-12 |
| Hessy | https://hessydental.com | Sitio oficial | 2026-10-12 |
| OdontoApp | https://odontoapp.com.ar/ | Sitio oficial | 2026-10-12 |
| AgendaPro | https://agendapro.com/ar/dental/software-odontologico | Sitio oficial, página para Argentina | 2026-10-12 |
| AgendaPro | https://agendapro.com/ar/planes | Página de precios | 2026-10-12 |
| AgendaPro | https://agendapro.com/ar/terminos-y-condiciones | Términos y condiciones | 2026-10-12 |
| YoFacturo | https://yo-facturo.com/clinicas | Sitio oficial y precios | 2026-10-12 |
| Gendu | https://www.gendu.com.ar/planes | Página de precios | 2026-10-12 |
| Turnito | https://www.turnito.app | Sitio oficial | 2026-10-12 |

### Latinoamérica y España

| Sistema | Fuente | Tipo | Fecha |
|---|---|---|---|
| Dentalink | https://www.softwaredentalink.com/ar | Sitio oficial, página para Argentina | 2026-10-12 |
| Dentalink | https://intercom.help/softwaredentalink/es | Centro de ayuda | 2026-10-12 |
| Clinicorp | https://www.clinicorp.com/ | Sitio oficial | 2026-10-12 |
| Clinicorp | https://www.clinicorp.com/planos | Página de precios | 2026-10-12 |
| Dentidesk | dentidesk.com | Sitio oficial y documentación | 2026-10-02 |
| Odeen | odeen.cl | Sitio oficial y precios | 2026-10-02 |
| Simples Dental | simplesdental.com | Sitio oficial y planes | 2026-10-02 |
| Simples Dental | ajuda.simplesdental.com | Centro de ayuda | 2026-10-02 |
| Doctocliq | doctocliq.com | Sitio oficial y precios | 2026-10-02 |
| Odontosys | odontosys.com | Sitio oficial | 2026-10-02 |
| Nubimed | nubimed.com | Sitio oficial | 2026-10-02 |

### Internacional

| Sistema | Fuente | Tipo | Fecha |
|---|---|---|---|
| Open Dental | https://www.opendental.com/site/fees.html | Página de precios | 2026-10-12 |
| Dentally | https://developer.dentally.co | Documentación técnica de la API | 2026-10-12 |
| Dentally | dentally.com | Sitio oficial y precios | 2026-10-02 |
| Dentrix / Dentrix Ascend | dentrix.com | Sitio oficial | 2026-10-02 |
| Curve Dental | curvedental.com | Sitio oficial | 2026-10-02 |
| tab32 | tab32.com | Sitio oficial y precios | 2026-10-02 |
| Archy | archy.com | Sitio oficial y precios | 2026-10-02 |
| CareStack | carestack.com | Sitio oficial | 2026-10-02 |
| NexHealth | nexhealth.com | Sitio oficial | 2026-10-02 |
| Medesk | medesk.net | Sitio oficial | 2026-10-02 |

### Documentos del proyecto

- `discovery/discovery.md`: resultado estructurado de la etapa de Discovery (checklist de once puntos).
- `discovery/analisis-competitivo.md`: relevamiento original del 2026-10-02 del que sale este informe.
