FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish src/FleetWise.Api/FleetWise.Api.csproj -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app .
ENV ASPNETCORE_URLS=http://+:8080 \
    ConnectionStrings__FleetWise="Data Source=/tmp/fleetwise.db"
EXPOSE 8080
ENTRYPOINT ["dotnet", "FleetWise.Api.dll"]
