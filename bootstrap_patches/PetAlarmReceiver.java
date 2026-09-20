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
        NotificationManager mgr = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        mgr.createNotificationChannel(new NotificationChannel(
                "pseudopet_default", "PseudoPet",
                NotificationManager.IMPORTANCE_HIGH));
        Notification n = new Notification.Builder(context, "pseudopet_default")
                .setContentTitle(intent.getStringExtra("title"))
                .setContentText(intent.getStringExtra("msg"))
                .setSmallIcon(context.getApplicationInfo().icon)
                .setAutoCancel(true)
                .build();
        mgr.notify((int) (System.currentTimeMillis() % 100000), n);
    }
}
