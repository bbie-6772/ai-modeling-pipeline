"""Analytic synthetic constraints, never a human approval or an inferred design."""
def contract(reference_sha, dimensions=None):
    provenance = dict(basis='observed', description='Analytic synthetic fixture, not production evidence',
                      reference_ids=['design'])
    return dict(schema_version='shape-contract-v1',asset_id='synthetic-robot',design_revision='fixture',units='m',
                references={'design':dict(path='reference.txt',sha256=reference_sha,view='text')},
                parts={'body':dict(objects=['Body'],observations=[provenance])},
                dimensions={'body':dict(provenance,size=dimensions or [1,1,.2],tolerance=.0001)},
                uncertainties=[])
