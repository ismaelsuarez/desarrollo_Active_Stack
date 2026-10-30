from sqlalchemy import Column, Integer, MetaData, String, Table

from app.infrastructure.db.base import Base


def test_base_metadata_has_canonical_naming_convention():
    convention = Base.metadata.naming_convention
    assert convention is not None
    assert "ix" in convention
    assert "uq" in convention
    assert "ck" in convention
    assert "fk" in convention
    assert "pk" in convention


def test_naming_convention_generates_predictable_names():
    metadata = Base.metadata
    test_table = Table(
        "tabla_prueba",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("codigo", String, unique=True),
    )
    # Check generated constraints have naming convention applied
    pk_name = test_table.primary_key.name
    assert pk_name == "pk_tabla_prueba"
    # Find unique constraint
    unique = next(iter(test_table.constraints - {test_table.primary_key}))
    assert unique.name == "uq_tabla_prueba_codigo"
