using TaleWorlds.CampaignSystem;
using TaleWorlds.Library;
using TaleWorlds.MountAndBlade;

namespace StoryMode
{
    public class StoryModeManager
    {
        public static StoryModeManager Current => null;
        public MainStoryLine MainStoryLine => null;
    }

    public class MainStoryLine
    {
        public StoryModePhases.ThirdPhase ThirdPhase => null;
    }
}

namespace StoryMode
{
    public abstract class StoryModeQuestBase : QuestBase
    {
        protected StoryModeQuestBase(string questId, Hero questGiver, CampaignTime duration, int rewardGold)
            : base(questId, questGiver, duration, rewardGold)
        {
        }
    }
}

namespace StoryMode.StoryModePhases
{
    public class ThirdPhase
    {
        public MBReadOnlyList<Kingdom> OppositionKingdoms => null;
    }
}

namespace StoryMode.Quests.FirstPhase
{
    public abstract class SupportKingdomQuest : QuestBase
    {
        protected SupportKingdomQuest(string questId, Hero questGiver, CampaignTime duration, int rewardGold)
            : base(questId, questGiver, duration, rewardGold)
        {
        }

        private void MainStoryLineChosen()
        {
        }
    }
}

namespace StoryMode.GameComponents
{
    public class StoryModeAgentDecideKilledOrUnconsciousModel : DefaultAgentDecideKilledOrUnconsciousModel
    {
    }
}
