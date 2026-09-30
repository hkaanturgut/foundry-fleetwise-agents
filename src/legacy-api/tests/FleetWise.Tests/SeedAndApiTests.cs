using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using FleetWise.Api.Data;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace FleetWise.Tests;

public class SeedDataTests
{
    [Fact]
    public void Tenant_two_has_no_dot_inspector()
    {
        // The demo relies on this gap: /speckit-clarify should ask what happens when no technician has the skill.
        using var t = new TestDatabase();

        var hasInspector = t.Db.Technicians.AsEnumerable()
            .Any(x => x.TenantId == 2 && x.Skills.Contains("DotInspector"));

        Assert.False(hasInspector);
    }

    [Fact]
    public void Seed_contains_the_planted_injection_note()
    {
        using var t = new TestDatabase();

        Assert.Contains(t.Db.MaintenanceRecords, r => r.TechnicianNotes.StartsWith("Ignore previous rules"));
    }

    [Fact]
    public void Seed_is_deterministic()
    {
        using var a = new TestDatabase();
        using var b = new TestDatabase();

        var first = a.Db.Vehicles.OrderBy(v => v.Id).Select(v => v.UnitNumber + v.OdometerKm).ToList();
        var second = b.Db.Vehicles.OrderBy(v => v.Id).Select(v => v.UnitNumber + v.OdometerKm).ToList();

        Assert.Equal(first, second);
    }
}

public class ApiTests : IClassFixture<ApiTests.Factory>
{
    private readonly HttpClient _client;

    public ApiTests(Factory factory) => _client = factory.CreateClient();

    [Fact]
    public async Task Health_is_ok()
    {
        var response = await _client.GetAsync("/health");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Overdue_report_returns_vehicles()
    {
        var json = await _client.GetFromJsonAsync<JsonElement>("/api/reports/overdue");
        Assert.True(json.GetProperty("count").GetInt32() > 0);
    }

    [Fact]
    public async Task Unknown_vehicle_is_404()
    {
        var response = await _client.GetAsync("/api/vehicles/9999");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    public sealed class Factory : WebApplicationFactory<Program>
    {
        private readonly SqliteConnection _connection = new("Data Source=:memory:");

        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            _connection.Open();
            builder.ConfigureServices(services =>
            {
                var descriptor = services.Single(d => d.ServiceType == typeof(DbContextOptions<FleetWiseDbContext>));
                services.Remove(descriptor);
                services.AddDbContext<FleetWiseDbContext>(o => o.UseSqlite(_connection));
            });
        }

        protected override void Dispose(bool disposing)
        {
            base.Dispose(disposing);
            _connection.Dispose();
        }
    }
}
