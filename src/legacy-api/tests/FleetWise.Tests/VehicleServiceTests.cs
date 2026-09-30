using FleetWise.Api.Services;

namespace FleetWise.Tests;

public class VehicleServiceTests
{
    [Fact]
    public async Task GetAll_returns_seeded_fleet()
    {
        using var t = new TestDatabase();
        var service = new VehicleService(t.Db);

        var vehicles = await service.GetAllAsync();

        Assert.Equal(50, vehicles.Count);
    }

    [Fact]
    public async Task Characterization_GetAll_returns_every_tenant()
    {
        // Characterization test: documents CURRENT legacy behavior, not desired behavior.
        // There is no tenant isolation today. A spec-driven change should flip this test.
        using var t = new TestDatabase();
        var service = new VehicleService(t.Db);

        var tenants = (await service.GetAllAsync()).Select(v => v.TenantId).Distinct().OrderBy(id => id);

        Assert.Equal(new[] { 1, 2 }, tenants);
    }

    [Fact]
    public async Task UpdateOdometer_rejects_going_backwards()
    {
        using var t = new TestDatabase();
        var service = new VehicleService(t.Db);
        var vehicle = (await service.GetByIdAsync(1))!;

        await Assert.ThrowsAsync<ArgumentException>(() => service.UpdateOdometerAsync(1, vehicle.OdometerKm - 1));
    }

    [Fact]
    public async Task UpdateOdometer_returns_null_for_unknown_vehicle()
    {
        using var t = new TestDatabase();
        var service = new VehicleService(t.Db);

        Assert.Null(await service.UpdateOdometerAsync(9999, 100));
    }
}
