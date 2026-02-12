# Archive All The Things \o| - The Thingiverse Thing Downloader

A Python script to download and archive your Things from [Thingiverse](https://www.thingiverse.com), including all files, images, metadata, comments, and license information.

## Features

- Download a single Thing by ID
- Download all published Things by a user
- Incremental updates - only downloads new/changed content
- Creates organized directory structure for each Thing:
  - `files/` - All downloadable STL, SCAD, and other files
  - `images/` - All images (display/large size preferred)
  - `README.md` - Formatted metadata, description, instructions, ancestors, and remixes
  - `COMMENTS.md` - All user comments
  - `LICENSE.md` - License information with summary
  - `metadata.json` - Raw API response data
- Throttling to avoid API rate limits
- Force re-download option

## Installation

### From Source

Clone the repository and install:

```bash
git clone https://github.com/tbuser/archiveallthethings.git
cd archiveallthethings
pip install -e .
```

This installs the `archiveallthethings` command.

### Requirements

- Python 3.6+
- `requests` library (installed automatically)

## Getting a Thingiverse Auth Token

To use this script, you need an API token from Thingiverse.

### Step 1: Create a Thingiverse App

1. Go to [https://www.thingiverse.com/developers](https://www.thingiverse.com/developers)
2. Log in with your Thingiverse account
3. Click **"Create an App"** or go to [https://www.thingiverse.com/apps/create](https://www.thingiverse.com/apps/create)
4. Fill in the application details:
   - **App Name**: Choose any name (e.g., "My Thing Downloader")
   - **Description**: Brief description of your use case
   - **App URL**: Can be `http://localhost` for personal use
   - **Callback URL**: Can be `http://localhost/callback` for personal use
5. Click **"Create App"**

### Step 2: Get Your App Token

After creating your app:

1. Go to your app's settings page
2. Find the **"App Token"** (also called Access Token)
3. Copy this token - it's a long alphanumeric string

### Step 3: Configure the Token

You can provide your token in two ways:

**Option A: Environment Variable (Recommended)**

```bash
export THINGIVERSE_TOKEN="your_token_here"
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

**Option B: Command-Line Argument**

```bash
archiveallthethings --token your_token_here --thing 161161
```

**Important:** Keep your token private. Never commit it to version control or share it publicly.

## Usage

After installation, use the `archiveallthethings` command (or `python archiveallthethings.py` if running directly).

### Download a Single Thing

```bash
archiveallthethings --thing 161161
```

### Download All Things by a User

```bash
archiveallthethings --user tbuser
```

### Specify Output Directory

```bash
archiveallthethings --thing 161161 --output ./my_downloads
```

### Force Re-download

By default, the script skips Things that haven't changed since the last download. Use `--force` to re-download everything:

```bash
archiveallthethings --thing 161161 --force
```

### Adjust Throttle Delay

When downloading multiple Things, adjust the delay between downloads (default: 1 second):

```bash
archiveallthethings --user tbuser --throttle 2.0
```

### All Options

```
usage: archiveallthethings [-h] (--thing ID | --user USERNAME) [--output DIR]
                              [--throttle SECONDS] [--force] [--token TOKEN]

Download Things from Thingiverse

options:
  -h, --help            show this help message and exit
  --thing ID, -t ID     Download a specific thing by ID
  --user USERNAME, -u USERNAME
                        Download all published things by a user
  --output DIR, -o DIR  Output directory (default: current directory)
  --throttle SECONDS    Seconds to wait between downloads (default: 1.0)
  --force, -f           Force re-download even if thing is unchanged
  --token TOKEN         Thingiverse API token (or set THINGIVERSE_TOKEN env var)
```

## Output Structure

For each Thing downloaded, the script creates a directory structure like:

```
thing_name/
├── README.md           # Metadata, description, instructions, links
├── COMMENTS.md         # User comments
├── LICENSE.md          # License information
├── metadata.json       # Raw API data
├── files/
│   ├── model.stl
│   ├── model.scad
│   └── ...
└── images/
    ├── main_image.jpg
    ├── detail_1.jpg
    └── ...
```

### README.md Contents

- Thing name and ID
- Creator information
- Dates (added, modified)
- License
- Statistics (likes, downloads, views, makes, remixes, comments)
- Tags
- Description
- Instructions
- File list with sizes
- Image gallery
- Ancestors (things this was remixed from)
- Remixes (things remixed from this)

## Incremental Updates

The script tracks what has been downloaded using the `modified` timestamp from Thingiverse:

1. **First run**: Downloads everything
2. **Subsequent runs**:
   - Checks if Thing has been modified since last download
   - Skips unchanged Things entirely
   - For changed Things, skips files/images that already exist locally
3. **With `--force`**: Re-downloads everything regardless of timestamps

This makes it efficient to periodically sync your local archive with Thingiverse.

## Examples

Download a specific Thing:
```bash
archiveallthethings -t 161161 -o ./archive
```

Archive all Things from a user:
```bash
archiveallthethings -u tbuser -o ./tbuser_archive --throttle 1.5
```

Update existing archive (only downloads changes):
```bash
archiveallthethings -u tbuser -o ./tbuser_archive
```

Force full re-download:
```bash
archiveallthethings -t 161161 -o ./archive --force
```

## Rate Limiting

Thingiverse has API rate limits. The script includes:

- Configurable throttle delay between Thing downloads (default: 1 second)
- Automatic throttling during user thing list pagination

If you encounter rate limit errors (HTTP 429), increase the `--throttle` value.

## License

Please respect Thingiverse's Terms of Service and the licenses of the Things you download. DBAD.
