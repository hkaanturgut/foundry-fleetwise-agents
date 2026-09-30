using FleetWise.Api.Models;
using FleetWise.Api.Services;

namespace FleetWise.Tests;

// User Story 1: see what needs service now (spec FR-001 to FR-003, FR-005).
public class DispatcherServiceTests
{
    [Fact]
    public async Task T008_distance_overdue_oil_change_is_listed_with_km_overdue()
    {
        using var t = new TestDatabase();
        var van = t.AddVehicle(1, "LightDuty", odometerKm: 50_000, unitNumber: "T-VAN-1");
        t.AddFreshRecords(van, except: "OilChange");
        t.AddRecord(van, "OilChange", daysAgo: 30, odometerKm: 41_000); // 9,000 km since, interval 8,000

        var lines = await new DispatcherService(t.Db, t.Clock).GetLinesAsync(tenantId: 1);

        var line = Assert.Single(lines, l => l.VehicleId == van.Id);
        Assert.Equal("OilChange", line.ServiceType);
        Assert.Equal(DispatchStatus.Overdue, line.Status);
        Assert.Equal(DispatchTrigger.Distance, line.Trigger);
        Assert.Equal(1_000, line.KmOverdue);
    }

    [Fact]
    public async Task T009_date_due_in_five_days_is_listed_as_due_soon()
    {
        using var t = new TestDatabase();
        var truck = t.AddVehicle(1, "HeavyDuty", odometerKm: 300_000, unitNumber: "T-TRK-1");
        t.AddFreshRecords(truck, except: "BrakeInspection");
        t.AddRecord(truck, "BrakeInspection", daysAgo: 175, odometerKm: 299_000); // interval 180 days

        var lines = await new DispatcherService(t.Db, t.Clock).GetLinesAsync(tenantId: 1);

        var line = Assert.Single(lines, l => l.VehicleId == truck.Id);
        Assert.Equal(DispatchStatus.DueSoon, line.Status);
        Assert.Equal(DispatchTrigger.Date, line.Trigger);
        Assert.Equal(5, line.DaysUntilDue);
    }

    [Fact]
    public async Task T010_tenant_one_never_sees_tenant_two_vehicles()
    {
        using var t = new TestDatabase();
        var other = t.AddVehicle(2, "LightDuty", odometerKm: 90_000, unitNumber: "T-OTHER-1"); // no history: due

        var lines = await new DispatcherService(t.Db, t.Clock).GetLinesAsync(tenantId: 1);

        Assert.NotEmpty(lines);
        Assert.DoesNotContain(lines, l => l.VehicleId == other.Id);
        var tenantOneIds = t.Db.Vehicles.Where(v => v.TenantId == 1).Select(v => v.Id).ToHashSet();
        Assert.All(lines, l => Assert.Contains(l.VehicleId, tenantOneIds));
    }

    [Fact]
    public async Task T011_open_work_order_marks_the_line_already_handled()
    {
        using var t = new TestDatabase();
        var van = t.AddVehicle(1, "LightDuty", odometerKm: 50_000, unitNumber: "T-VAN-2");
        t.AddFreshRecords(van, except: "OilChange");
        t.AddRecord(van, "OilChange", daysAgo: 30, odometerKm: 41_000);
        t.Db.WorkOrders.Add(new WorkOrder { TenantId = 1, VehicleId = van.Id, ServiceType = "OilChange", Status = WorkOrderStatus.Draft, CreatedOn = t.Clock.UtcNow });
        t.Db.SaveChanges();

        var lines = await new DispatcherService(t.Db, t.Clock).GetLinesAsync(tenantId: 1);

        var line = Assert.Single(lines, l => l.VehicleId == van.Id);
        Assert.Equal(DispatchStatus.AlreadyHandled, line.Status);
    }

    [Fact]
    public async Task No_history_is_due_now_and_flagged()
    {
        using var t = new TestDatabase();
        var van = t.AddVehicle(1, "LightDuty", odometerKm: 12_000, unitNumber: "T-VAN-3");
        t.AddFreshRecords(van, except: "TireRotation");

        var lines = await new DispatcherService(t.Db, t.Clock).GetLinesAsync(tenantId: 1);

        var line = Assert.Single(lines, l => l.VehicleId == van.Id);
        Assert.Equal(DispatchTrigger.NoHistory, line.Trigger);
        Assert.Equal(DispatchStatus.Overdue, line.Status);
    }

    [Fact]
    public async Task Schedule_based_list_finds_more_than_the_legacy_fixed_rule()
    {
        // SC-002: the dispatcher uses real schedules; the legacy report uses one hard-coded rule.
        using var t = new TestDatabase();

        var lines = await new DispatcherService(t.Db, t.Clock).GetLinesAsync(tenantId: 1);

        Assert.True(lines.Select(l => l.VehicleId).Distinct().Count() > 4);
    }
}
