# staff-management Specification

## Purpose

Administra las cuentas del personal que usa el consultorio, con un rol único y asociación controlada entre profesionales de agenda y sus cuentas.

## Requirements

### Requirement: Solo el administrador gestiona usuarios del personal
La API MUST permitir al rol `administrador` crear, listar y editar usuarios de personal del consultorio autenticado; las escrituras de otros roles MUST responder 403.

#### Scenario: Administrador crea cuenta de personal
- **GIVEN** un administrador autenticado
- **WHEN** crea una cuenta con rol permitido para personal
- **THEN** la cuenta queda asociada al consultorio del `Principal`

#### Scenario: Otro rol no administra usuarios
- **GIVEN** un usuario autenticado sin rol administrador
- **WHEN** intenta crear o editar un usuario del personal
- **THEN** la API responde 403 y no modifica datos

### Requirement: Cuentas del personal tienen un rol único no paciente
El alta de personal MUST aceptar solo los roles `administrador`, `recepcion`, `profesional` y `administrativo`; el rol `paciente`, roles múltiples y `consultorio_id` enviado por cliente MUST rechazarse.

#### Scenario: Alta con rol paciente
- **WHEN** el administrador intenta crear una cuenta de personal con rol `paciente`
- **THEN** la API responde 422 y no crea usuario

#### Scenario: Rechazo de campos ajenos
- **WHEN** una solicitud de alta incluye `consultorio_id` o varios roles
- **THEN** la API responde 422 sin crear la cuenta

### Requirement: Desactivar personal conserva historial
Al desactivar una cuenta de personal, la API MUST impedir su uso futuro sin eliminar el usuario ni sus relaciones históricas.

#### Scenario: Desactivación de cuenta
- **GIVEN** una cuenta activa con historial asociado
- **WHEN** el administrador la desactiva
- **THEN** queda inactiva y el registro e historial permanecen

### Requirement: Agenda profesional se asocia a cuenta compatible
Cada profesional de agenda MUST asociarse a una cuenta del mismo consultorio con rol `profesional` o `administrador`; un usuario tendrá como máximo una ficha de profesional.

#### Scenario: Cuenta de administrador atiende
- **WHEN** el administrador asocia su cuenta a su profesional de agenda
- **THEN** la asociación se acepta y conserva el rol único de la cuenta

#### Scenario: Rol incompatible
- **WHEN** se intenta asociar una cuenta de recepción, paciente o administrativo a una agenda profesional
- **THEN** la operación se rechaza sin cambiar la asociación
