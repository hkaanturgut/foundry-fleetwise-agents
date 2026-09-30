using FleetWise.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Api.Data;

public class FleetWiseDbContext : DbContext
{
    public FleetWiseDbContext(DbContextOptions<FleetWiseDbContext> options) : base(options)
    {
    }

    public DbSet<Tenant> Tenants => Set<Tenant>();
    public DbSet<Vehicle> Vehicles => Set<Vehicle>();
    public DbSet<MaintenanceSchedule> MaintenanceSchedules => Set<MaintenanceSchedule>();
    public DbSet<MaintenanceRecord> MaintenanceRecords => Set<MaintenanceRecord>();
    public DbSet<Technician> Technicians => Set<Technician>();
    public DbSet<WorkOrder> WorkOrders => Set<WorkOrder>();
    public DbSet<DispatchDecision> DispatchDecisions => Set<DispatchDecision>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Vehicle>()
            .HasMany(v => v.MaintenanceRecords)
            .WithOne()
            .HasForeignKey(r => r.VehicleId);

        modelBuilder.Entity<WorkOrder>()
            .Property(w => w.Status)
            .HasConversion<string>();

        modelBuilder.Entity<DispatchDecision>()
            .Property(d => d.Outcome)
            .HasConversion<string>();

        // Legacy: no global query filter for TenantId. Every query sees every tenant.
    }
}
