package cn.pokeserver;

import org.bukkit.ChatColor;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.event.entity.EntityTargetLivingEntityEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;




public class PokeListener implements Listener {

    private final PokePlugin plugin;

    public PokeListener(PokePlugin plugin) {
        this.plugin = plugin;
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        plugin.getManager().giveStarter(e.getPlayer());
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent e) {
        plugin.getManager().dismiss(e.getPlayer());
        plugin.getBattleManager().removePlayer(e.getPlayer());
    }

    
    @EventHandler(priority = EventPriority.HIGH)
    public void onInteractEntity(PlayerInteractEntityEvent e) {
        
        if (!plugin.getManager().isPokeball(e.getPlayer().getInventory().getItemInMainHand())) return;
        Entity clicked = e.getRightClicked();
        if (!plugin.getManager().isWildPokemon(clicked)) {
            e.getPlayer().sendMessage(ChatColor.GRAY + "（这不是一只野生的宝可梦，无法捕捉）");
            e.setCancelled(true);
            return;
        }
        e.setCancelled(true);
        plugin.getManager().catchAttempt(e.getPlayer(), clicked);
    }

    
    @EventHandler
    public void onDamage(EntityDamageEvent e) {
        if (plugin.getManager().isWildPokemon(e.getEntity())) {
            e.setCancelled(true);
            return;
        }
        Player owner = plugin.getManager().getSummonedOwner(e.getEntity());
        if (owner != null) {
            e.setCancelled(true);
        }
    }

    
    @EventHandler
    public void onDamageByEntity(EntityDamageByEntityEvent e) {
        if (e.getDamager() instanceof Player) {
            Player p = (Player) e.getDamager();
            Player owner = plugin.getManager().getSummonedOwner(e.getEntity());
            if (owner != null && owner.equals(p)) {
                e.setCancelled(true);
            }
        }
    }

    
    @EventHandler
    public void onTarget(EntityTargetLivingEntityEvent e) {
        if (plugin.getManager().isWildPokemon(e.getEntity())
                && e.getTarget() instanceof Player) {
            e.setCancelled(true);
        }
    }

    
    @EventHandler
    public void onKill(EntityDeathEvent e) {
        Entity killer = e.getEntity().getKiller();
        if (killer instanceof Player) {
            Player p = (Player) killer;
            plugin.getManager().removeWild(e.getEntity());
            if (plugin.getManager().hasSummoned(p)) {
                PokeSpecies.Species sp = PokeSpecies.get(e.getEntityType());
                int exp = (sp != null) ? 4 + sp.baseExp / 3 : 4;
                plugin.getManager().grantExp(p, exp);
            }
        } else {
            plugin.getManager().removeWild(e.getEntity());
        }
    }
}
