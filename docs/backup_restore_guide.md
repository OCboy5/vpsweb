# VPSWeb Backup and Restore Guide v0.3.1

This guide provides comprehensive instructions for backing up and restoring VPSWeb repository system data, including database, configuration, source code, and generated outputs.

## Table of Contents

1. [Overview](#overview)
2. [Backup System](#backup-system)
3. [Restore System](#restore-system)
4. [Automated Backups](#automated-backups)
5. [Disaster Recovery](#disaster-recovery)
6. [Troubleshooting](#troubleshooting)

## Overview

The VPSWeb backup and restore system provides comprehensive protection for:

- **Database**: SQLite database with all poems, translations, and workflow data
- **Configuration**: YAML config files, environment variables, and settings
- **Source Code**: Application source code (excluding build artifacts)
- **Outputs**: Generated translations, JSON files, and processed data
- **Documentation**: Project documentation, tests, and key project files

### Prerequisites

- **Unix-like environment** (Linux, macOS, Windows with WSL)
- **Required tools**: `sqlite3`, `tar`, `rsync`, `python3`
- **Sufficient disk space**: Typically 10-100MB per backup depending on data size

## Backup System

### Manual Backup

#### Complete Backup

```bash
# Create a complete compressed backup
./scripts/backup.sh
```

This creates:
- Compressed tarball: `backups/vpsweb_backup_YYYYMMDD_HHMMSS.tar.gz`
- Automatic cleanup of old backups (keeps last 10)
- Integrity verification
- Backup metadata with git commit info

#### Backup Options

```bash
# Show help
./scripts/backup.sh --help

# Create backup without compression (for testing)
./scripts/backup.sh --no-compress

# Verify existing backup integrity
./scripts/backup.sh --verify-only
./scripts/backup.sh --verify-only backups/vpsweb_backup_20231019_120000.tar.gz
```

### Backup Contents

Each backup includes:

```
vpsweb_backup_YYYYMMDD_HHMMSS/
├── backup_info.json          # Backup metadata and info
├── vpsweb.db                 # SQLite database file
├── vpsweb_schema.sql         # Database schema dump
├── config/                   # Configuration files
│   ├── config/              # YAML configuration
│   ├── .env                 # Environment variables
│   └── .env.local           # Local environment
├── src/                      # Source code (clean)
│   └── vpsweb/              # Application source
├── outputs/                  # Generated outputs
│   ├── json/                # Translation results
│   ├── markdown/            # Formatted translations
│   └── wechat_articles/     # WeChat articles
└── docs/                     # Documentation and tests
    ├── docs/                # Project documentation
    ├── tests/               # Test suite
    ├── README.md            # Project README
    ├── pyproject.toml       # Dependencies
    └── CLAUDE.md            # AI assistant guide
```

### Backup Metadata

Each backup includes `backup_info.json` with:

```json
{
    "backup_name": "vpsweb_backup_20231019_120000",
    "timestamp": "20231019_120000",
    "created_at": "2023-10-19T12:00:00+00:00",
    "project_root": "/path/to/vpsweb",
    "git_commit": "a1b2c3d4e5f6...",
    "git_branch": "main",
    "git_status": " M src/vpsweb/webui/main.py",
    "python_version": "Python 3.9.0",
    "os_info": "Linux hostname 5.15.0...",
    "backup_contents": {
        "database": "SQLite database and schema dump",
        "config": "Configuration files and environment variables",
        "source": "Source code (excluding build artifacts)",
        "outputs": "Generated outputs and translations",
        "docs": "Documentation, tests, and project files"
    }
}
```

## Restore System

### Manual Restore

#### List Available Backups

```bash
# Show all available backups with details
./scripts/restore.sh --list
```

Output:
```
Available backups:

1. vpsweb_backup_20231019_120000.tar.gz
   Size: 45MB, Date: 2023-10-19 12:00:00
   Git: a1b2c3d, Created: 2023-10-19T12:00:00

2. vpsweb_backup_20231019_080000.tar.gz
   Size: 44MB, Date: 2023-10-19 08:00:00
   Git: f5e6d7c, Created: 2023-10-19T08:00:00
```

#### Complete Restore

```bash
# Interactive restore (prompts for overwrites)
./scripts/restore.sh backups/vpsweb_backup_20231019_120000.tar.gz

# Force restore (no prompts)
./scripts/restore.sh --force backups/vpsweb_backup_20231019_120000.tar.gz
```

#### Selective Restore

```bash
# Restore only database
./scripts/restore.sh --db-only backups/vpsweb_backup_20231019_120000.tar.gz

# Restore only configuration
./scripts/restore.sh --config-only backups/vpsweb_backup_20231019_120000.tar.gz

# Restore only source code
./scripts/restore.sh --source-only backups/vpsweb_backup_20231019_120000.tar.gz

# Restore only outputs
./scripts/restore.sh --outputs-only backups/vpsweb_backup_20231019_120000.tar.gz
```

#### Dry Run (Preview)

```bash
# Show what would be restored without doing it
./scripts/restore.sh --dry-run backups/vpsweb_backup_20231019_120000.tar.gz
```

### Restore Verification

After restore, verify the system:

```bash
# 1. Check database integrity
sqlite3 data/vpsweb.db 'PRAGMA integrity_check;'

# 2. Verify database contents
sqlite3 data/vpsweb.db 'SELECT COUNT(*) FROM poems;'
sqlite3 data/vpsweb.db 'SELECT COUNT(*) FROM translations;'

# 3. Test application
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
python -m vpsweb.webui.main --help

# 4. Run database migrations if needed
alembic upgrade head

# 5. Install dependencies
poetry install
```

## Automated Backups

### Cron Job Setup

#### Daily Backups

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/vpsweb && ./scripts/backup.sh

# Add weekly backup verification (Sundays at 3 AM)
0 3 * * 0 cd /path/to/vpsweb && ./scripts/backup.sh --verify-only
```

#### Weekly Full Backup with Notification

```bash
#!/bin/bash
# backup_weekly.sh - Enhanced weekly backup with notifications

BACKUP_SCRIPT="/path/to/vpsweb/scripts/backup.sh"
LOG_FILE="/path/to/vpsweb/logs/backup.log"
EMAIL="admin@example.com"

# Create backup
cd /path/to/vpsweb
$BACKUP_SCRIPT > "$LOG_FILE" 2>&1

# Check if backup succeeded
if [[ $? -eq 0 ]]; then
    echo "Weekly backup completed successfully" | mail -s "VPSWeb Backup Success" "$EMAIL"
else
    echo "Weekly backup failed. Check log: $LOG_FILE" | mail -s "VPSWeb Backup FAILED" "$EMAIL"
fi
```

### Systemd Timer (Linux)

#### Create service file

```ini
# /etc/systemd/system/vpsweb-backup.service
[Unit]
Description=VPSWeb Backup Service
After=network.target

[Service]
Type=oneshot
User=vpsweb
WorkingDirectory=/path/to/vpsweb
ExecStart=/path/to/vpsweb/scripts/backup.sh
StandardOutput=journal
StandardError=journal
```

#### Create timer file

```ini
# /etc/systemd/system/vpsweb-backup.timer
[Unit]
Description=Run VPSWeb backup daily at 2 AM
Requires=vpsweb-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

#### Enable and start timer

```bash
sudo systemctl enable vpsweb-backup.timer
sudo systemctl start vpsweb-backup.timer

# Check status
sudo systemctl status vpsweb-backup.timer
sudo systemctl list-timers
```

## Disaster Recovery

### Complete System Recovery

#### 1. Assess Damage

```bash
# Check what's available
ls -la /path/to/vpsweb/
ls -la /path/to/backups/

# Verify latest backup
./scripts/restore.sh --list
```

#### 2. Prepare New Environment

```bash
# Create new directory
mkdir -p /new/path/to/vpsweb
cd /new/path/to/vpsweb

# Clone repository if source code restore needed
git clone https://github.com/your-org/vpsweb.git .
git checkout main  # or appropriate branch
```

#### 3. Restore from Backup

```bash
# Copy backup file to new location
cp /path/to/backups/vpsweb_backup_latest.tar.gz ./

# Complete restore
./scripts/restore.sh --force vpsweb_backup_latest.tar.gz
```

#### 4. Verify System

```bash
# Database integrity
sqlite3 data/vpsweb.db 'PRAGMA integrity_check;'

# Application functionality
poetry install
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
python -m vpsweb.webui.main --help

# Run tests
python -m pytest tests/ -v
```

#### 5. Update Configuration

```bash
# Update environment files if needed
vim .env.local

# Update configuration if paths changed
vim config/default.yaml
```

### Partial Recovery Scenarios

#### Database Corruption Only

```bash
# Stop application
pkill -f "vpsweb"

# Restore database only
./scripts/restore.sh --db-only --force backups/vpsweb_backup_latest.tar.gz

# Restart application
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
python -m vpsweb.webui.main
```

#### Configuration Lost

```bash
# Restore configuration only
./scripts/restore.sh --config-only --force backups/vpsweb_backup_latest.tar.gz

# Update environment variables if needed
vim .env.local
```

#### Generated Outputs Lost

```bash
# Restore outputs only
./scripts/restore.sh --outputs-only --force backups/vpsweb_backup_latest.tar.gz
```

## Troubleshooting

### Common Issues

#### Permission Errors

```bash
# Make scripts executable
chmod +x scripts/backup.sh scripts/restore.sh

# Fix ownership
sudo chown -R $USER:$USER /path/to/vpsweb
```

#### Disk Space Issues

```bash
# Check available space
df -h /path/to/backups

# Clean old backups manually
ls -la /path/to/backups/vpsweb_backup_*.tar.gz | tail -n +11 | xargs rm

# Reduce backup retention (edit backup.sh)
# Change: ls -1t vpsweb_backup_*.tar.gz | tail -n +11 | xargs -r rm
# To:      ls -1t vpsweb_backup_*.tar.gz | tail -n +6 | xargs -r rm  # Keep 5 instead of 10
```

#### Database Issues

```bash
# Check database integrity
sqlite3 data/vpsweb.db 'PRAGMA integrity_check;'

# If corrupted, try to recover
sqlite3 data/vpsweb.db ".recover" | sqlite3 data/vpsweb_recovered.db

# Test backup integrity
tar -tzf backups/vpsweb_backup_latest.tar.gz | head -10
```

#### Restore Verification

```bash
# Test restore without overwriting
./scripts/restore.sh --dry-run backups/vpsweb_backup_latest.tar.gz

# Verify backup contents
tar -tzf backups/vpsweb_backup_latest.tar.gz | grep -E "(db|json|config)"
```

### Log Files

Monitor backup and restore operations:

```bash
# Backup logs (if using cron/systemd)
journalctl -u vpsweb-backup -f

# Application logs
tail -f logs/vpsweb.log

# System logs
tail -f /var/log/syslog | grep backup
```

### Performance Optimization

#### Large Database Backups

For databases > 1GB:

```bash
# Use SQLite backup API instead of file copy
# Already implemented in backup.sh: sqlite3 "$db_file" ".backup '${backup_db}'"

# Consider excluding old data
# Edit backup.sh to add WHERE clauses in SQL dump
```

#### Network Storage

For storing backups on network storage:

```bash
# Mount network storage
sudo mount -t nfs nas-server:/backups /mnt/backups

# Update backup script to use network location
# Edit BACKUP_DIR in backup.sh: BACKUP_DIR="/mnt/backups/vpsweb"
```

#### Compression Options

For faster backups with less compression:

```bash
# Use faster compression (bigger files, faster)
# Edit backup.sh: tar -cf "${BACKUP_NAME}.tar" "$BACKUP_NAME"
# Then: gzip -1 "${BACKUP_NAME}.tar"

# Or use different compression tool
# Edit backup.sh: tar -cjf "${BACKUP_NAME}.tar.bz2" "$BACKUP_NAME"
```

## Best Practices

1. **Regular Backups**: Schedule daily automated backups
2. **Test Restores**: Monthly test restore procedures on non-production system
3. **Offsite Storage**: Store critical backups offsite or in cloud storage
4. **Monitor Logs**: Regularly check backup logs for errors
5. **Document Changes**: Update this guide when making backup system changes
6. **Version Control**: Keep backup scripts in version control
7. **Access Control**: Limit backup access to authorized personnel
8. **Retention Policy**: Define and enforce backup retention policies

## Support

For backup and restore issues:

1. Check this guide first
2. Review log files for error messages
3. Verify system requirements are met
4. Test with a small backup first
5. Contact system administrator if issues persist

---

**Version**: 0.3.1
**Last Updated**: 2023-10-19
**Compatibility**: VPSWeb v0.3.1+