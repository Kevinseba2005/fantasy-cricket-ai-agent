import json
import boto3
import urllib.request
from datetime import datetime, timezone, timedelta

# =============================================
# ⚙️ CONFIGURATION
# =============================================
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:816344831012:FantasyCricketAlerts"
REGION = "us-east-1"
BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
CRICBUZZ_API = "https://cricbuzz-live.vercel.app"

# =============================================
# AWS CLIENTS
# =============================================
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)


def get_ist_now():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)


# =============================================
# 🏏 CRICKET DATA
# =============================================
def fetch_matches():
    """Cricbuzz la try pannum, fail aana fallback use pannum"""
    urls = [
        f"{CRICBUZZ_API}/matches/live",
        f"{CRICBUZZ_API}/matches/upcoming"
    ]
    
    for url in urls:
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
                if data:
                    print(f"✅ Got {len(data)} matches from Cricbuzz!")
                    return data
        except Exception as e:
            print(f"⚠️ Cricbuzz API failed: {e}")
            continue
    return None


def get_fallback_data():
    """Backup data - ALWAYS WORKS!"""
    return [
        {
            "title": "India vs Australia, 2nd T20I",
            "team1": "India",
            "team2": "Australia",
            "venue": "M.A. Chidambaram Stadium, Chennai",
            "format": "T20",
            "date": "2026-07-17",
            "time": "7:30 PM IST",
            "team1_players": [
                "Rohit Sharma (BAT)", "Virat Kohli (BAT)", "Suryakumar Yadav (BAT)",
                "KL Rahul (WK)", "Hardik Pandya (AR)", "Ravindra Jadeja (AR)",
                "Axar Patel (AR)", "Jasprit Bumrah (BOWL)", "Mohammed Siraj (BOWL)",
                "Yuzvendra Chahal (BOWL)", "Arshdeep Singh (BOWL)"
            ],
            "team2_players": [
                "Travis Head (BAT)", "David Warner (BAT)", "Steve Smith (BAT)",
                "Josh Inglis (WK)", "Glenn Maxwell (AR)", "Marcus Stoinis (AR)",
                "Mitchell Marsh (AR)", "Pat Cummins (BOWL)", "Mitchell Starc (BOWL)",
                "Adam Zampa (BOWL)", "Josh Hazlewood (BOWL)"
            ]
        },
        {
            "title": "England vs South Africa, 1st ODI",
            "team1": "England",
            "team2": "South Africa",
            "venue": "The Oval, London",
            "format": "ODI",
            "date": "2026-07-17",
            "time": "3:30 PM IST",
            "team1_players": [
                "Jos Buttler (WK)", "Joe Root (BAT)", "Harry Brook (BAT)",
                "Ben Stokes (AR)", "Jonny Bairstow (BAT)", "Moeen Ali (AR)",
                "Liam Livingstone (AR)", "Mark Wood (BOWL)", "Jofra Archer (BOWL)",
                "Adil Rashid (BOWL)", "Reece Topley (BOWL)"
            ],
            "team2_players": [
                "Quinton de Kock (WK)", "Aiden Markram (BAT)", "Rassie van der Dussen (BAT)",
                "Heinrich Klaasen (BAT)", "David Miller (BAT)", "Marco Jansen (AR)",
                "Keshav Maharaj (AR)", "Kagiso Rabada (BOWL)", "Anrich Nortje (BOWL)",
                "Lungi Ngidi (BOWL)", "Tabraiz Shamsi (BOWL)"
            ]
        }
    ]


# =============================================
# 🧠 AI - BEDROCK FANTASY TEAM
# =============================================
def build_match_context(match):
    title = match.get("title", "Cricket Match")
    team1 = match.get("team1", "Team A")
    team2 = match.get("team2", "Team B")
    venue = match.get("venue", "TBA")
    fmt = match.get("format", "T20")
    date = match.get("date", "Today")
    time = match.get("time", "TBA")
    t1_players = match.get("team1_players", [])
    t2_players = match.get("team2_players", [])
    
    context = f"""
🏏 Match: {title}
📍 Venue: {venue}
📅 Date: {date} | Time: {time}
🎯 Format: {fmt}

--- TEAM 1: {team1} ---
"""
    for p in t1_players:
        context += f"  • {p}\n"
    context += f"\n--- TEAM 2: {team2} ---\n"
    for p in t2_players:
        context += f"  • {p}\n"
    return context


def generate_fantasy_team(match_context):
    prompt = f"""You are an expert Fantasy Cricket advisor (Dream11 style).
Based on the following match, create the BEST fantasy team.

{match_context}

Create a fantasy team with EXACTLY 11 players:
- 1-2 Wicket-keepers (WK)
- 3-5 Batsmen (BAT)
- 1-3 All-rounders (AR)
- 3-5 Bowlers (BOWL)

For each player provide:
1. Name
2. Role (WK/BAT/AR/BOWL)
3. Team
4. Why selected (1 line reason)
5. Fantasy points potential (High/Medium)

Also provide:
- 🏆 CAPTAIN (2x points) - with detailed reasoning
- ⭐ VICE-CAPTAIN (1.5x points) - with detailed reasoning
- 🎲 DIFFERENTIAL PICK - low-owned game-changer
- ❌ PLAYERS TO AVOID (2-3) - with reason

End with:
- Match prediction
- Confidence level (Low/Medium/High)

Use emojis, keep it fun and readable!"""

    request_body = json.dumps({
        "messages": [
            {"role": "user", "content": [{"text": prompt}]}
        ],
        "inferenceConfig": {
            "maxTokens": 2048,
            "temperature": 0.7,
            "topP": 0.9
        }
    })

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=request_body
    )

    response_body = json.loads(response["body"].read())
    return response_body["output"]["message"]["content"][0]["text"]


def generate_pitch_report(match_context):
    prompt = f"""You are a cricket pitch and conditions expert.
Based on this match info, give a brief pitch report:

{match_context}

Include:
1. 🏟️ Pitch type (batting/bowling friendly, pace/spin)
2. 📊 Average scores at this venue
3. 🎯 Key fantasy tips based on conditions
4. ⚡ Toss advice - bat first or chase?
5. 🌤️ Weather impact

Keep under 120 words. Be specific and actionable."""

    request_body = json.dumps({
        "messages": [
            {"role": "user", "content": [{"text": prompt}]}
        ],
        "inferenceConfig": {
            "maxTokens": 512,
            "temperature": 0.6,
            "topP": 0.9
        }
    })

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=request_body
    )

    response_body = json.loads(response["body"].read())
    return response_body["output"]["message"]["content"][0]["text"]


# =============================================
# 📧 EMAIL SEND - SNS
# =============================================
def send_fantasy_email(match_title, pitch_report, fantasy_team):
    """SNS use panni email anuppum"""
    
    date_str = get_ist_now().strftime("%A, %B %d, %Y")
    time_str = get_ist_now().strftime("%I:%M %p IST")
    
    message = f"""
🏏 FANTASY CRICKET AI ADVISOR
{'='*50}
🤖 Your AI agent worked while you slept!
📅 {date_str} | ⏰ {time_str}
{'='*50}

📋 MATCH: {match_title}

{'─'*50}
🏟️ AI PITCH REPORT:
{'─'*50}
{pitch_report}

{'─'*50}
⭐ AI FANTASY TEAM RECOMMENDATION:
{'─'*50}
{fantasy_team}

{'='*50}
🤖 Powered by: AWS Bedrock (Nova) + Lambda + EventBridge + SNS
🏏 Built for AWS Weekend Agent Challenge 2026
⚠️ For entertainment only. Play responsibly!
{'='*50}
"""
    
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"🏏 Fantasy Team Ready! {match_title} | {date_str}"[:100],
        Message=message
    )
    print("📧 Email sent via SNS successfully!")


# =============================================
# 🚀 MAIN LAMBDA HANDLER
# =============================================
def lambda_handler(event, context):
    """Main function - EventBridge daily trigger"""
    
    print("=" * 50)
    print("🏏 FANTASY CRICKET AI ADVISOR AGENT")
    print(f"⏰ Time: {get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 50)
    
    try:
        # Step 1: Fetch matches
        print("\n📡 Step 1: Fetching cricket matches...")
        matches = fetch_matches()
        
        if not matches:
            print("⚠️ Using fallback data...")
            matches = get_fallback_data()
        
        print(f"🏏 Processing {len(matches)} match(es)")
        results = []
        
        # Process top 2 matches
        for match in matches[:2]:
            match_title = match.get("title", "Cricket Match")
            print(f"\n⚡ Processing: {match_title}")
            
            # Build context
            match_context = build_match_context(match)
            
            # AI Pitch Report
            print("🏟️ Generating pitch report...")
            pitch_report = generate_pitch_report(match_context)
            print("✅ Pitch report ready!")
            
            # AI Fantasy Team
            print("🧠 Generating fantasy team...")
            fantasy_team = generate_fantasy_team(match_context)
            print("✅ Fantasy team ready!")
            
            # Send Email via SNS!
            print("📧 Sending email via SNS...")
            send_fantasy_email(match_title, pitch_report, fantasy_team)
            print("✅ Email sent!")
            
            results.append({"match": match_title, "status": "sent"})
        
        print(f"\n✅ DONE! {len(results)} fantasy team(s) sent!")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Fantasy advice sent for {len(results)} match(es)!",
                "matches": results,
                "timestamp": get_ist_now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }



