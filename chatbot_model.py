# Bu kodni courses/models.py fayliga qo'shing (oxiriga)

class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='chat_messages', null=True, blank=True)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username}: {self.message[:50]}'
