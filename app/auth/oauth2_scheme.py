from fastapi.security import OAuth2PasswordBearer

# tokenUrl tells Swagger UI where to POST credentials to get a token.
# It must match the router path that handles the password flow.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
