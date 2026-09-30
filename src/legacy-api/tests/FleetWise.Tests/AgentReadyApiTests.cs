using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using FleetWise.Api.Services;

namespace FleetWise.Tests;

// US2, US3 and T026: the endpoints the Foundry agents call.
public class TechnicianMatcherTests
{
    [Fact]
    public async Task Never_suggests_another_tenants_technician()
    {
        using var t = new TestDatabase();
        // Tenant 2 has no DotInspector, tenant 1 does (Tom Becker).
        var suggestion = await new TechnicianMatcher(t.Db, t.Clock).SuggestAsync(2, "DotInspector");

        Assert.True(suggestion.NoQualifiedTechnician);
        Assert.Null(suggestion.TechnicianId);
    }

    [Fact]
    public async Task Suggests_a_qualified_technician_in_the_same_tenant()
    {
        using var t = new TestDatabase();
        var suggestion = await new TechnicianMatcher(t.Db, t.Clock).SuggestAsync(1, "DotInspector");

        Assert.Equal("Tom Becker", suggestion.TechnicianName);
    }
}

public class DispatchDecisionApiTests : IClassFixture<ApiTests.Factory>
{
    private readonly HttpClient _client;

    public DispatchDecisionApiTests(ApiTests.Factory factory) => _client = factory.CreateClient();

    private HttpRequestMessage Req(HttpMethod m, string url, string tenant, string? role = null, object? body = null)
    {
        var r = new HttpRequestMessage(m, url);
        r.Headers.Add("X-Tenant-Id", tenant);
        if (role is not null) { r.Headers.Add("X-User-Role", role); r.Headers.Add("X-User-Name", "demo-manager"); }
        if (body is not null) r.Content = JsonContent.Create(body);
        return r;
    }

    [Fact]
    public async Task Unknown_tenant_is_400()
    {
        var res = await _client.SendAsync(Req(HttpMethod.Get, "/api/dispatch", "999"));
        Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
    }

    [Fact]
    public async Task Approve_requires_fleet_manager_then_blocks_double_booking()
    {
        var list = await (await _client.SendAsync(Req(HttpMethod.Get, "/api/dispatch", "1"))).Content.ReadFromJsonAsync<JsonElement>();
        var line = list.GetProperty("lines").EnumerateArray().First(l => l.GetProperty("status").GetString() != "AlreadyHandled");
        var body = new { vehicleId = line.GetProperty("vehicleId").GetInt32(), serviceType = line.GetProperty("serviceType").GetString() };

        Assert.Equal(HttpStatusCode.Forbidden, (await _client.SendAsync(Req(HttpMethod.Post, "/api/dispatch/approve", "1", "Technician", body))).StatusCode);
        Assert.Equal(HttpStatusCode.Created, (await _client.SendAsync(Req(HttpMethod.Post, "/api/dispatch/approve", "1", "FleetManager", body))).StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, (await _client.SendAsync(Req(HttpMethod.Post, "/api/dispatch/approve", "1", "FleetManager", body))).StatusCode);
    }
}
