const client = ZAFClient.init();

client.on('app.registered', async () => {
  try {
    const ticketData = await client.get('ticket.id');
    const ticketId = ticketData['ticket.id'];

    const container = document.getElementById('groupTimeSummary');
    if (!container) {
      console.error('❌ groupTimeSummary element not found in DOM.');
      return;
    }

    container.innerText = '🔄 Fetching group time...';

    client.on('ticket.status.changed', async (status) => {
      if (status === 'resolved') {
        showGroupTimes(ticketId);
      }
    });

    showGroupTimes(ticketId);
  } catch (err) {
    console.error('Initialization failed:', err);
    document.getElementById('groupTimeSummary').innerText = '❌ Failed to initialize app.';
  }
});

async function showGroupTimes(ticketId) {
  const container = document.getElementById('groupTimeSummary');
  const url = `/proxy/api/v2/tickets/${ticketId}/audits.json`;

  try {
    const response = await client.request({
      url: url,
      type: 'GET',
      dataType: 'json'
    });

    console.log("Raw response:", response);

    if (!response.audits) {
      container.innerText = '⚠️ No audits found.';
      return;
    }

    const audits = response.audits.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    let groupTimes = {};
    let currentGroup = null;
    let startTime = null;

    audits.forEach(audit => {
      const time = new Date(audit.created_at);
      audit.events.forEach(event => {
        if (event.field_name === 'group_id') {
          if (currentGroup && startTime) {
            const diff = (time - startTime) / 1000;
            groupTimes[currentGroup] = (groupTimes[currentGroup] || 0) + diff;
          }
          currentGroup = event.value;
          startTime = time;
        }
      });
    });

    if (currentGroup && startTime) {
      const now = new Date();
      const diff = (now - startTime) / 1000;
      groupTimes[currentGroup] = (groupTimes[currentGroup] || 0) + diff;
    }

    if (Object.keys(groupTimes).length === 0) {
      container.innerText = '⏱️ No group time data available.';
      return;
    }

    let display = '<strong>Group Time Summary:</strong><ul>';
    for (const [groupId, seconds] of Object.entries(groupTimes)) {
      const hrs = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      display += `<li>Group ${groupId}: ${hrs}h ${mins}m</li>`;
    }
    display += '</ul>';

    container.innerHTML = display;

  } catch (error) {
    console.error('Failed to fetch or process audit logs:', error);
    container.innerText = `❌ Error loading group times: ${error.message || error}`;
  }
}
