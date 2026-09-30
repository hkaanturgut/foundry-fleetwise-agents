using FleetWise.Api.Models;
using FleetWise.Api.Services;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Tests;

public class WorkOrderServiceTests
{
    [Fact]
    public async Task Create_starts_as_draft_with_clock_time()
    {
        using var t = new TestDatabase();
        var service = new WorkOrderService(t.Db, t.Clock);

        var created = await service.CreateAsync(new CreateWorkOrderRequest(1, 5, "OilChange", null));

        Assert.Equal(WorkOrderStatus.Draft, created.Status);
        Assert.Equal(t.Clock.UtcNow, created.CreatedOn);
    }

    [Fact]
    public async Task Characterization_Create_accepts_unknown_vehicle()
    {
        // Characterization test: legacy validation is thin. Documented here so a spec can change it deliberately.
        using var t = new TestDatabase();
        var service = new WorkOrderService(t.Db, t.Clock);

        var created = await service.CreateAsync(new CreateWorkOrderRequest(1, 9999, "OilChange", null));

        Assert.True(created.Id > 0);
    }

    [Fact]
    public async Task Schedule_moves_draft_to_scheduled()
    {
        using var t = new TestDatabase();
        var service = new WorkOrderService(t.Db, t.Clock);

        var scheduled = await service.ScheduleAsync(2, t.Clock.UtcNow.AddDays(1), 7);

        Assert.Equal(WorkOrderStatus.Scheduled, scheduled!.Status);
        Assert.Equal(7, scheduled.TechnicianId);
    }

    [Fact]
    public async Task Schedule_rejects_non_draft()
    {
        using var t = new TestDatabase();
        var service = new WorkOrderService(t.Db, t.Clock);

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.ScheduleAsync(1, t.Clock.UtcNow, 1));
    }

    [Fact]
    public async Task Complete_records_maintenance_at_current_odometer()
    {
        using var t = new TestDatabase();
        var service = new WorkOrderService(t.Db, t.Clock);
        var before = await t.Db.MaintenanceRecords.CountAsync(r => r.VehicleId == 3);

        var completed = await service.CompleteAsync(1, "Oil and filter changed.");

        Assert.Equal(WorkOrderStatus.Completed, completed!.Status);
        Assert.Equal(before + 1, await t.Db.MaintenanceRecords.CountAsync(r => r.VehicleId == 3));
    }
}
