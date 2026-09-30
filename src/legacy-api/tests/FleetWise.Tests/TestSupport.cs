using FleetWise.Api.Data;
using FleetWise.Api.Models;
using FleetWise.Api.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Tests;

public sealed class FixedClock : IClock
{
    public FixedClock(DateTime utcNow) => UtcNow = utcNow;
    public DateTime UtcNow { get; set; }
}

/// <summary>
/// A real SQLite database in memory, seeded with the demo data. One per test.
/// </summary>
public sealed class TestDatabase : IDisposable
{
    private readonly SqliteConnection _connection;

    public TestDatabase()
    {
        _connection = new SqliteConnection("Data Source=:memory:");
        _connection.Open();
        Clock = new FixedClock(new DateTime(2026, 10, 1, 12, 0, 0, DateTimeKind.Utc));
        var options = new DbContextOptionsBuilder<FleetWiseDbContext>().UseSqlite(_connection).Options;
        Db = new FleetWiseDbContext(options);
        Db.Database.EnsureCreated();
        SeedData.Seed(Db, Clock);
        Db.ChangeTracker.Clear();
    }

    public FleetWiseDbContext Db { get; }
    public FixedClock Clock { get; }

    // T002: helpers to build precise scenarios on top of the seed, for any tenant.
    public Vehicle AddVehicle(int tenantId, string vehicleClass, int odometerKm, string unitNumber)
    {
        var vehicle = new Vehicle
        {
            TenantId = tenantId,
            UnitNumber = unitNumber,
            Make = "Test",
            Model = "Unit",
            Year = 2024,
            OdometerKm = odometerKm,
            VehicleClass = vehicleClass
        };
        Db.Vehicles.Add(vehicle);
        Db.SaveChanges();
        return vehicle;
    }

    public void AddRecord(Vehicle vehicle, string serviceType, int daysAgo, int odometerKm)
    {
        Db.MaintenanceRecords.Add(new MaintenanceRecord
        {
            TenantId = vehicle.TenantId,
            VehicleId = vehicle.Id,
            ServiceType = serviceType,
            PerformedOn = Clock.UtcNow.Date.AddDays(-daysAgo),
            OdometerKm = odometerKm
        });
        Db.SaveChanges();
    }

    /// <summary>Adds records for every schedule of the class so only the service under test is due.</summary>
    public void AddFreshRecords(Vehicle vehicle, params string[] except)
    {
        foreach (var schedule in Db.MaintenanceSchedules.Where(s => s.VehicleClass == vehicle.VehicleClass).ToList())
        {
            if (!except.Contains(schedule.ServiceType))
            {
                AddRecord(vehicle, schedule.ServiceType, daysAgo: 1, odometerKm: vehicle.OdometerKm);
            }
        }
    }

    public void Dispose()
    {
        Db.Dispose();
        _connection.Dispose();
    }
}
