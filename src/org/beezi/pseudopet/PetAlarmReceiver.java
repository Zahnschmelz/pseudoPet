package org.beezi.pseudopet;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;

public class PetAlarmReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        String title = intent.getStringExtra("title");
        String msg   = intent.getStringExtra("msg");
        if (title == null) title = "PseudoPet";
        if (msg == null)   msg   = "(Extras verloren - PendingIntent-Problem!)";

        NotificationManager mgr = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        mgr.createNotificationChannel(new NotificationChannel(
                "pseudopet_default", "PseudoPet",
                NotificationManager.IMPORTANCE_HIGH));
        Notification n = new Notification.Builder(context, "pseudopet_default")
                .setContentTitle(title)          // <<< die Variablen nutzen!
                .setContentText(msg)              // <<<
                .setSmallIcon(context.getApplicationInfo().icon)
                .setAutoCancel(true)
                .build();
        mgr.notify((int) (System.currentTimeMillis() % 100000), n);
    }
}
