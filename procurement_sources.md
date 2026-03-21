# Top 10 Procurement Sources for IT/Software Tenders

Curated list for a software company (AI, Web, APIs, Products, Consulting) targeting high-value tenders in Costa Rica and Central America.

Last updated: 2026-03-20

---

## #1 — SICOP (Costa Rica Government)

**URL:** https://www.sicop.go.cr

Costa Rica's mandatory government procurement platform. 285 of 293 public institutions publish here. ~78 IT/software tenders per month. 12.5% of GDP (~$6B/year) passes through SICOP.

**Tipos de licitaciones IT:**
- Desarrollo de software custom (web, mobile)
- Consultoría IT y gobernanza
- Licenciamiento (Microsoft, Oracle, SAP)
- AI y tecnología emergente
- Ciberseguridad
- Soporte IT y mantenimiento
- Cloud y hosting

**Principales compradores IT:**
- ICE/Grupo ICE (telecom, 5G, energía)
- CCSS (healthcare IT, presupuesto $12B/año)
- Banco Nacional, BCR, Banco Popular (banking IT)
- INS (modernización de sistemas de seguros)
- UNED, UCR, UNA (IT universitario)
- Banco Central (sistemas financieros)
- Ministerio de Hacienda (Hacienda Digital)

**Ejemplos de presupuestos:**
- Oracle licensing: $19.5M
- Horas analista de sistemas (mobile/web): $1.44M
- Microsoft EES licenses: $336K
- Firewall/seguridad: $288K
- Ciberseguridad: $92K
- Consultoría gobernanza IT: $26K

**Scraping:**
- Método: JSON API (ya implementado)
- Search: `POST https://prod-api.sicop.go.cr/bid/api/v1/public/epCartel/searchEpCartels` (sin auth)
- Detail: `POST https://prod-api.sicop.go.cr/bid/api/v1/public/epCartel/findById` (sin auth)
- Bulk: `https://dlsaobservatorioprod.blob.core.windows.net/fs-synapse-observatorio-produccion/Zip/{yyyymm}.zip` (CSV diario, datos desde 2010)
- Dificultad: **Baja**

---

## #2 — BID/IDB (Banco Interamericano de Desarrollo)

**URL:** https://www.iadb.org/en/how-we-can-work-together/procurement/procurement-projects/procurement-notices

Largest source of development financing for Latin America. ~$4.5B/year in procurement, 12,000+ contracts. Empresas CR ya ganan contratos: Addax Software ($76K, 2025), Ideas Únicas Digitales ($45K, 2024).

**Proyectos activos en CR:**
- CR-L1152: Sistema Educativo ($150M + $7.5M grant) — transformación tecnológica MEP
- IDB Invest + ICE: Digitalización eléctrica ($100M) — smart meters 300K usuarios
- CR-T1225: Licitaciones Inteligentes ($187,500) — plataforma AI de procurement
- CR-T1263: Habilidades Digitales ($600,000) — innovación educativa digital

**Tipos de licitaciones IT:**
- Desarrollo de software (método QCBS)
- Consultoría en transformación digital
- Data analytics y machine learning
- Migración a cloud
- Implementación ERP/IFMIS
- Plataformas de gobierno digital
- Evaluación de ciberseguridad

**Presupuestos:** $45K — $8.4M para contratos IT

**Scraping:**
- Método: CKAN API
- Contract Awards: `https://data.iadb.org/api/3/action/package_show?id=cc69283d-6257-49e7-a76d-090119f3a995` (sin auth, CSV/JSON)
- Awarded Contracts: https://projectprocurement.iadb.org/en/awarded-contracts
- Dificultad: **Baja**

---

## #3 — Banco Mundial (World Bank)

**URL:** https://projects.worldbank.org/en/projects-operations/procurement

Mejor API de procurement disponible. $850M+ en proyectos activos en CR con componentes tecnológicos masivos.

**Proyectos activos en CR:**
- Hacienda Digital (P172352) — $156.64M total, $23M+ en tecnología: IFMIS, sistema tributario TRIBU-CR, aduanas Atena, analytics con ML, API bus, cloud migration
- Results in Education — $200M: plataformas pedagógicas para 90,000 docentes, herramientas digitales para 18,000 empleados MEP
- Fiscal Management & Green Growth (P508347) — $300M: modernización fiscal

**Tipos de licitaciones IT:**
- Sistemas de gestión financiera (IFMIS)
- Sistemas de administración tributaria
- Sistemas aduaneros
- Data analytics con machine learning
- Government Services Bus (SOA/API)
- Cloud migration y disaster recovery
- Learning management systems

**Presupuestos:** $50K — $23M+ para componentes IT

**Scraping:**
- Método: REST API (la mejor disponible)
- Endpoint: `GET https://search.worldbank.org/api/v2/procnotices?format=json&countrycode_exact=CR&rows=50`
- Sin autenticación, JSON, actualización diaria
- Parámetros: `countrycode_exact`, `rows`, `os` (offset), `strdate`, `enddate`
- Dificultad: **Baja**

---

## #4 — BCIE (Banco Centroamericano de Integración Económica)

**URL:** https://adquisiciones.bcie.org

Banco dedicado a Centroamérica. CR es miembro fundador. Switch Software (empresa tica) ganó contrato para plataforma digital (React, .NET, Azure, AI). Fondo ICO-BCIE de $150M para transición digital.

**Ejemplos reales IT:**
- Cloud Migration Solution (activo)
- Plataforma Digital BCIE (Switch Software, CR)
- ICO-BCIE $150M: empresas de "tecnología e IA para transformación digital"
- Fibra óptica frontera a frontera: $24.4M
- Plataforma AI para emprendedores CR

**Tipos de licitaciones IT:**
- Soluciones de migración a nube
- Desarrollo de plataformas digitales
- Soluciones de AI
- Infraestructura de comunicaciones
- Licencias de software y equipos

**Presupuestos:** $50K — $24M

**Scraping:**
- Método: Web scraping
- Portal: https://adquisiciones.bcie.org/en/procurement-notice (tabla con filtro por país)
- Supplier Portal: https://proveedoreserp.bcie.org/ (Oracle ERP)
- Open Data: https://datosabiertos.bcie.org/en/dataset/?tags=licitaciones
- Dificultad: **Media**

---

## #5 — Sistema ONU (UNGM + UNDP + UNOPS)

**UNGM:** https://www.ungm.org/Public/Notice
**UNDP:** https://procurement-notices.undp.org/
**UNOPS:** https://esourcing.unops.org/

Tres portales complementarios. UNOPS tiene su Global Shared Service Centre en San José (compra IT localmente). UNDP tiene oficina en CR con proyectos digitales. UNGM agrega 40+ agencias ($14B+/año). Registro gratuito (Nivel 1 suficiente).

**Tipos de licitaciones IT:**
- Plataformas de gobierno digital
- Data analytics y dashboards
- Aplicaciones móviles
- Sistemas GIS y mapeo
- Proyectos AI/ML (NLP, predictive analytics)
- Desarrollo web y CMS
- Consultoría en transformación digital
- Soporte IT (local al GSSC en San José)

**Presupuestos:** $5K — $5M. LTAs (contratos marco 2-3 años) son muy valiosos.

**Scraping:**
- UNDP RSS Feed: `https://procurement-notices.undp.org/proc_notices_rss_feed.cfm` (horario, filtro país CRI, sin auth) — **Baja**
- UNGM: Angular app, AJAX/JSON interno — **Media**
- UNOPS eSourcing: Web scraping — **Media**

---

## #6 — ICE / Grupo ICE (Portal PEL)

**URL:** https://apps.grupoice.com/PEL/

EL mayor comprador de IT en Costa Rica ($200M+/año estimado). Única institución con sistema propio (PEL) además de SICOP. Cubre ICE, CNFL, RACSA.

**Ejemplos reales:**
- Licitación 5G: $249M (Huawei, Samsung, Ericsson, Nokia como oferentes)
- Contrato EDUS con CCSS: $201M
- Renovaciones SAP, Oracle constantes
- Programas de adquisición anuales en CSV/XLS

**Tipos de licitaciones IT:**
- Infraestructura 5G/Telecom
- Enterprise software (SAP, Oracle)
- Desarrollo de plataformas custom
- Servicios de infraestructura IT
- Managed services
- Equipos de red

**Presupuestos:** $100K — $249M

**Scraping:**
- PEL Portal: https://apps.grupoice.com/PEL/ (puede requerir login)
- Transparencia: https://www.grupoice.com/wps/portal/ICE/Transparencia/compras
- También publica en SICOP
- Dificultad: **Media-Alta**

---

## #7 — CCSS (Caja Costarricense de Seguro Social)

**URL:** https://www.ccss.sa.cr/datos-abiertos-licitaciones

Mayor empleador de Centroamérica. Presupuesto $12B/año. Contrato EDUS ($201M) venció en 2024 — nueva licitación esperada. Publica datos abiertos en múltiples formatos.

**Ejemplos reales:**
- EDUS (Expediente Digital Único en Salud): $201M — necesita reemplazo
- Redimed (imagenología digital): $29.5M
- SAP ERP mantenimiento: $1.1M/año

**Tipos de licitaciones IT:**
- Sistemas de información de salud (EHR/EMR)
- Plataformas de imagenología médica
- Sistemas ERP (SAP)
- Sistemas de gestión hospitalaria
- Sistemas de información de laboratorio
- Plataformas de telemedicina
- Ciberseguridad

**Presupuestos:** $1M — $201M

**Scraping:**
- Open Data: https://www.ccss.sa.cr/datos-abiertos-licitaciones (CSV, XLSX, JSON, PDF, RDF, SQL)
- También publica en SICOP
- Dificultad: **Baja**

---

## #8 — Bancos Estatales (BNCR, BCR, Banco Popular)

**Portales:**
- Banco Nacional: https://www.bncr.fi.cr/proveeduria
- BCR: https://www.bcrcompras.com/
- Banco Popular: https://www.bancopopular.fi.cr/contratacion-administrativa-banco-popular/
- Banco Central: https://www.bccr.fi.cr/contrataciones

Banking IT es extremadamente caro. Gasto combinado estimado $50-100M+/año.

**Ejemplos reales:**
- Banco Nacional: $57M contrato infraestructura Cisco (nueva licitación esperada 2H 2026)
- Banco Nacional: adopción biometría FacePhi
- BCR: licitación sistema ERP
- Banco Popular: renovaciones Oracle constantes

**Tipos de licitaciones IT:**
- Core banking systems
- Infraestructura de red
- Ciberseguridad
- Autenticación biométrica
- Sistemas ERP
- Canales de banca digital
- Apps móviles bancarias

**Presupuestos:** $5M — $57M+

**Scraping:**
- Todos publican en SICOP — misma API, filtrar por código de institución
- Dificultad: **Baja**

---

## #9 — EU Funding & Tenders Portal

**URL:** https://ec.europa.eu/info/funding-tenders/opportunities/portal/

La UE firmó MoU de conectividad satelital con CR (EUR 22.5M). Programa BELLA extiende fibra óptica Europa-CR. EU-LAC Digital Alliance cubre AI, e-governance, 5G. Fondos no atados (empresas CR pueden ganar).

**Contexto:**
- EU-Central America Association Agreement (mayo 2024)
- EUR 864M en inversión apalancada para conectividad satelital en LatAm
- Laboratorio de ciberforense y testbed 5G en Costa Rica
- Fondos untied: empresas CR elegibles directamente

**Tipos de licitaciones IT:**
- Infraestructura de conectividad digital
- Aplicaciones AI para gobernanza
- Ciberseguridad (laboratorio ciberforense)
- Testbeds 5G
- Plataformas de e-governance
- Soluciones de conectividad satelital

**Presupuestos:** EUR 100K — 5M+ por contrato

**Scraping:**
- TED API: https://ted.europa.eu/api/documentation/index.html (REST, JSON/XML, EU Login gratuito)
- EU F&T API: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis
- Bulk XML: https://ted.europa.eu/packages/daily/
- Dificultad: **Baja**

---

## #10 — CAF (Banco de Desarrollo de América Latina)

**URL:** https://www.caf.com/en/work-with-us/calls/

Costa Rica es miembro pleno. Licitación activa de digitalización de compras públicas abiertas (open source). Área estratégica dedicada a transformación digital del Estado.

**Ejemplos reales:**
- "Regional Agenda for Digitalization of Open Public Procurement" — desarrollo open source de 3 módulos IT
- Soluciones tecnológicas para salas multimedia (Panamá)
- Investigación sobre informalidad y digitalización (hasta $15K por proyecto)

**Tipos de licitaciones IT:**
- Desarrollo de software open source
- Plataformas de procurement digital
- Soluciones tecnológicas multimedia
- Consultoría en transformación digital

**Presupuestos:** $15K — $500K+

**Scraping:**
- Calls: https://www.caf.com/en/work-with-us/calls/
- Bids: https://www.caf.com/en/work-with-us/bids/
- Sin API, web scraping estándar
- Dificultad: **Media**

---

## Matriz de Prioridad de Scraping

### Con API (implementar primero):
| # | Fuente | Método | Auth |
|---|--------|--------|------|
| 1 | SICOP | JSON API (ya implementado) | Ninguna |
| 2 | World Bank | REST API JSON | Ninguna |
| 3 | IDB/BID | CKAN API CSV/JSON | Ninguna |
| 4 | EU/TED | REST API JSON/XML | EU Login gratuito |
| 5 | UNDP | RSS Feed | Ninguna |
| 6 | CCSS | Open data CSV/JSON | Ninguna |

### Con web scraping:
| # | Fuente | Dificultad |
|---|--------|------------|
| 7 | BCIE | Media (tablas HTML) |
| 8 | UNGM | Media (Angular/AJAX) |
| 9 | ICE/PEL | Media-Alta (posible login) |
| 10 | CAF | Media (HTML estándar) |

### Via SICOP API (sin trabajo extra):
- Bancos Estatales (BNCR, BCR, BP, BCCR)
- Todas las demás instituciones CR
