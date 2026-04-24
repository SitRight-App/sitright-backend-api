---
name: Historia de Usuario
about: Crear una HU del Product Backlog como issue trabajable
title: 'HU-XX: <Título corto>'
labels: 'user-story'
assignees: ''
---

## HU-XX: <Título>

**Epic:** E<N> - <Nombre del epic>
**MoSCoW:** Must / Should / Could / Won't
**Valor (Fibonacci):** 3 / 5 / 8 / 13 / 21
**Prioridad:** <número en el backlog>

## Descripción

**Como** <rol>,
**quiero** <objetivo>,
**para** <beneficio>.

## Criterios de Validación (Gherkin)

### Escenario 1: <Título del escenario>
**Dado que** <contexto>
**y** <contexto adicional>
**cuando** <acción>
**entonces** <resultado esperado>

### Escenario 2: <Título del escenario>
**Dado que** <contexto>
**cuando** <acción>
**entonces** <resultado esperado>

## Notas técnicas

**Bounded context:** <posture_capture | posture_classification | ...>
**Feature frontend:** <nombre del feature>

## Definición de Hecho (DoD)

- [ ] Código implementado en la rama `feature/HU-XX-<slug>`
- [ ] Tests agregados que cubren todos los escenarios Gherkin
- [ ] Tests pasando localmente
- [ ] Code review aprobado por el otro integrante
- [ ] Merge a `main` realizado
- [ ] `sitright-workspace/CLAUDE.md § What's Next` actualizado
