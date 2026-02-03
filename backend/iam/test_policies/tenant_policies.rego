package tenant.policies

allow = true if eq(input["user"]["attrs"]["dept"], "CS")
