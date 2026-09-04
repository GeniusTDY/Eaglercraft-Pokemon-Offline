package cn.pokeserver;

import org.bukkit.entity.EntityType;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;





public class PokeSpecies {

    
    public static class Species {
        public final String name;      
        public final double catchRate; 
        public final int baseExp;      
        public final EntityType evolveTo; 
        public final int evolveLevel;     

        public Species(String name, double catchRate, int baseExp, EntityType evolveTo, int evolveLevel) {
            this.name = name;
            this.catchRate = catchRate;
            this.baseExp = baseExp;
            this.evolveTo = evolveTo;
            this.evolveLevel = evolveLevel;
        }
    }

    private static final Map<EntityType, Species> MAP = new HashMap<>();

    static {
        
        reg(EntityType.CHICKEN,   "咯咯鸡", 0.90, 6,  EntityType.PIG, 10);
        reg(EntityType.PIG,       "哼哼猪", 0.80, 9,  EntityType.COW, 12);
        reg(EntityType.COW,       "哞哞牛", 0.70, 13, EntityType.HORSE, 18);
        reg(EntityType.SHEEP,     "绵绵羊", 0.75, 11, EntityType.LLAMA, 15);
        reg(EntityType.RABBIT,    "蹦蹦兔", 0.85, 7,  EntityType.SHEEP, 10);
        reg(EntityType.MUSHROOM_COW, "菇菇牛", 0.60, 14, null, 0);
        reg(EntityType.LLAMA,     "啵啵羊驼", 0.50, 17, null, 0);
        reg(EntityType.HORSE,     "哒哒马", 0.40, 22, null, 0);
        reg(EntityType.DONKEY,    "倔倔驴", 0.50, 16, null, 0);
        reg(EntityType.VILLAGER,  "憨憨村民", 0.50, 12, null, 0);
        reg(EntityType.IRON_GOLEM,"铁铁傀儡", 0.20, 35, null, 0);
        
        reg(EntityType.WOLF,      "汪汪狼", 0.55, 16, EntityType.HORSE, 20);
        reg(EntityType.OCELOT,    "喵喵猫", 0.60, 15, EntityType.WOLF, 12);
        reg(EntityType.BAT,       "夜夜蝙蝠", 0.70, 5,  null, 0);
        reg(EntityType.SQUID,     "墨墨鱿鱼", 0.60, 11, null, 0);
        reg(EntityType.POLAR_BEAR,"白白北极熊", 0.40, 19, null, 0);
        
        reg(EntityType.SLIME,     "弹弹史莱姆", 0.60, 12, EntityType.MAGMA_CUBE, 15);
        reg(EntityType.MAGMA_CUBE,"滚滚岩浆怪", 0.40, 19, null, 0);
        reg(EntityType.ZOMBIE,    "笨笨僵尸", 0.60, 13, EntityType.ZOMBIE_VILLAGER, 14);
        reg(EntityType.ZOMBIE_VILLAGER, "村霸僵尸", 0.50, 16, null, 0);
        reg(EntityType.PIG_ZOMBIE,"金金猪人", 0.45, 18, null, 0);
        reg(EntityType.SKELETON,  "咔咔骷髅", 0.55, 15, EntityType.WITHER_SKELETON, 20);
        reg(EntityType.WITHER_SKELETON, "黑黑凋零骷髅", 0.35, 22, null, 0);
        reg(EntityType.SPIDER,    "丝丝蜘蛛", 0.60, 14, EntityType.CAVE_SPIDER, 12);
        reg(EntityType.CAVE_SPIDER,"洞洞蜘蛛", 0.50, 16, null, 0);
        reg(EntityType.CREEPER,   "蹦蹦苦力怕", 0.45, 17, null, 0);
        reg(EntityType.ENDERMAN,  "长手末影人", 0.30, 24, null, 0);
        reg(EntityType.BLAZE,     "焰焰烈焰人", 0.35, 21, null, 0);
        reg(EntityType.GUARDIAN,  "刺刺守卫者", 0.40, 21, null, 0);
        reg(EntityType.ENDERMITE, "小小末影螨", 0.70, 9,  null, 0);
        reg(EntityType.SILVERFISH,"虫虫蠹鱼", 0.70, 9,  null, 0);
    }

    private static void reg(EntityType type, String name, double rate, int exp, EntityType evolveTo, int evolveLv) {
        MAP.put(type, new Species(name, rate, exp, evolveTo, evolveLv));
    }

    public static Species get(EntityType type) {
        return MAP.get(type);
    }

    public static boolean isPokemonType(EntityType type) {
        return MAP.containsKey(type);
    }

    public static Map<EntityType, Species> all() {
        return MAP;
    }

    
    private static final EntityType[] SAFE_POOL = {
            EntityType.CHICKEN, EntityType.PIG, EntityType.COW, EntityType.SHEEP,
            EntityType.RABBIT, EntityType.MUSHROOM_COW, EntityType.LLAMA,
            EntityType.HORSE, EntityType.DONKEY, EntityType.VILLAGER,
            EntityType.IRON_GOLEM, EntityType.WOLF, EntityType.OCELOT,
            EntityType.POLAR_BEAR
    };

    
    public static List<EntityType> wildPool() {
        List<EntityType> out = new ArrayList<>();
        for (EntityType t : SAFE_POOL) {
            if (MAP.containsKey(t)) out.add(t);
        }
        return out;
    }
}
