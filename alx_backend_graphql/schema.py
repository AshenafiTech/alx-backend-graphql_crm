import graphene
import CRMQuery  # Assuming CRMQuery is defined in the alx_backend_graphql_crm module

class Query(CRMQuery, graphene.ObjectType):
    hello = graphene.String()

    def resolve_hello(root, info):
        return "Hello, GraphQL!"

schema = graphene.Schema(query=Query)
