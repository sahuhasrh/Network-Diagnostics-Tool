import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import socket
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
import subprocess
import threading
import speedtest
from mpl_toolkits.basemap import Basemap
import requests  # For IP geolocation via ipinfo.io

class NetworkNavigator:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Navigator")
        self.root.geometry("800x600")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.details_tab = ttk.Frame(self.notebook)
        self.traceroute_tab = ttk.Frame(self.notebook)
        self.connections_tab = ttk.Frame(self.notebook)
        self.network_tools_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.details_tab, text='Network Details')
        self.notebook.add(self.traceroute_tab, text='Network Route')
        self.notebook.add(self.connections_tab, text='Connections')
        self.notebook.add(self.network_tools_tab, text='Network Tools')

        # Initialize tabs
        self.setup_details_tab()
        self.setup_traceroute_tab()
        self.setup_connections_tab()
        self.setup_network_tools_tab()
        
        # Cache for IP locations to reduce API calls
        self.ip_cache = {}
        
        # Start periodic updates
        self.update_data()

    def setup_details_tab(self):
        interface_frame = ttk.LabelFrame(self.details_tab, text="Network Interfaces")
        interface_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create Treeview for interface details
        self.interface_tree = ttk.Treeview(interface_frame, columns=('Interface', 'IP Address', 'Status'), show='headings')
        self.interface_tree.heading('Interface', text='Interface')
        self.interface_tree.heading('IP Address', text='IP Address')
        self.interface_tree.heading('Status', text='Status')
        self.interface_tree.pack(fill='both', expand=True)

    def setup_traceroute_tab(self):
        # Input frame
        input_frame = ttk.Frame(self.traceroute_tab)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="Target:").pack(side=tk.LEFT)
        self.target_entry = ttk.Entry(input_frame)
        self.target_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        self.target_entry.insert(0, "google.com")
        
        ttk.Button(input_frame, text="Trace", command=self.run_traceroute).pack(side=tk.LEFT)
        
        # Create canvas for traceroute graph
        self.trace_fig, self.trace_ax = plt.subplots(figsize=(8, 6))
        self.trace_canvas = FigureCanvasTkAgg(self.trace_fig, self.traceroute_tab)
        self.trace_canvas.get_tk_widget().pack(fill='both', expand=True)

    def setup_connections_tab(self):
        top_frame = ttk.Frame(self.connections_tab)
        top_frame.pack(fill='both', expand=True)

        # Connection table
        self.conn_tree = ttk.Treeview(self.connections_tab, 
                                    columns=('Local Address', 'Remote Address', 'Status'),
                                    show='headings')
        self.conn_tree.heading('Local Address', text='Local Address')
        self.conn_tree.heading('Remote Address', text='Remote Address')
        self.conn_tree.heading('Status', text='Status')
        self.conn_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Pie chart for connection status
        self.conn_fig, self.conn_ax = plt.subplots(figsize=(6, 4))
        self.conn_canvas = FigureCanvasTkAgg(self.conn_fig, self.connections_tab)
        self.conn_canvas.get_tk_widget().pack(fill='both', expand=True)

        # World map for remote connections
        self.world_map_fig, self.world_map_ax = plt.subplots(figsize=(8, 6))
        self.world_map_canvas = FigureCanvasTkAgg(self.world_map_fig, self.connections_tab)
        self.world_map_canvas.get_tk_widget().pack(fill='both', expand=True)

        # Set up Basemap for world map
        self.world_map = Basemap(projection='robin', lon_0=0, resolution='l', ax=self.world_map_ax)
        self.world_map.drawcoastlines()
        self.world_map.drawcountries()
        self.world_map.drawmapboundary(fill_color='lightblue')

    def setup_network_tools_tab(self):
        tool_frame = ttk.Frame(self.network_tools_tab)
        tool_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Speed Test Button
        ttk.Button(tool_frame, text="Run Speed Test", command=self.run_speed_test).pack(pady=5)
        
        # Ping Test Section
        ping_frame = ttk.LabelFrame(tool_frame, text="Ping Test")
        ping_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(ping_frame, text="Target:").pack(side=tk.LEFT)
        self.ping_target_entry = ttk.Entry(ping_frame)
        self.ping_target_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5)
        
        ttk.Button(ping_frame, text="Ping", command=self.run_ping_test).pack(side=tk.LEFT)

    def update_interface_chart(self):
        try:
            # Clear previous entries
            self.interface_tree.delete(*self.interface_tree.get_children())

            # Update network interface statistics
            stats = psutil.net_if_addrs()
            for iface, addresses in stats.items():
                ip_address = "N/A"
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        ip_address = addr.address
                status = '🟢 Connected' if psutil.net_if_stats()[iface].isup else '🔴 Disconnected'
                self.interface_tree.insert('', 'end', values=(iface, ip_address, status))
        except Exception as e:
            print(f"Error updating interface chart: {e}")

    def run_traceroute(self):
        target = self.target_entry.get()

        def trace():
            try:
                # Run traceroute for Windows
                result = subprocess.run(['tracert', target], capture_output=True, text=True)
                output = result.stdout

                # Parse traceroute output and create graph
                G = nx.Graph()
                prev_node = 'Start'
                G.add_node(prev_node)

                for line in output.split('\n')[4:]:  # Skip initial lines
                    if not line.strip():
                        continue

                    parts = line.split()
                    if len(parts) >= 3:
                        hop = parts[1]
                        label = parts[-1] if parts[-1].replace('.', '').isdigit() else parts[-1]
                        G.add_node(label)
                        G.add_edge(prev_node, label)
                        prev_node = label

                # Draw graph
                self.trace_ax.clear()
                pos = nx.spring_layout(G)
                nx.draw(G, pos, ax=self.trace_ax, with_labels=True, node_color='lightblue', node_size=500)
                self.trace_canvas.draw()
            except Exception as e:
                print(f"Error in traceroute: {e}")

        threading.Thread(target=trace).start()

    def run_speed_test(self):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download_speed = st.download() / 1e6  # Convert to Mbps
            upload_speed = st.upload() / 1e6  # Convert to Mbps
            print(f"Download Speed: {download_speed:.2f} Mbps, Upload Speed: {upload_speed:.2f} Mbps")
            messagebox.showinfo("Speed Test Result", f"Download: {download_speed:.2f} Mbps\nUpload: {upload_speed:.2f} Mbps")
        except Exception as e:
            print(f"Error in speed test: {e}")

    def run_ping_test(self):
        target = self.ping_target_entry.get()

        def ping():
            try:
                result = subprocess.run(['ping', '-n', '4', target], capture_output=True, text=True)
                output = result.stdout
                ping_time = None
                for line in output.splitlines():
                    if 'Average' in line:
                        ping_time = line.split('=')[-1].strip()
                if ping_time:
                    messagebox.showinfo("Ping Test Result", f"Ping: {ping_time} ")
                else:
                    messagebox.showinfo("Ping Test Result", "Ping failed.")
            except Exception as e:
                print(f"Error in ping test: {e}")

        threading.Thread(target=ping).start()

    def update_connections_chart(self):
        try:
            # Get connection statistics
            connections = psutil.net_connections()

            # Clear previous entries
            self.conn_tree.delete(*self.conn_tree.get_children())
            status_counts = {'ESTABLISHED': 0, 'CLOSE_WAIT': 0, 'LISTEN': 0, 'TIME_WAIT': 0}

            # Update the connection table and plot remote locations on the world map
            for conn in connections:
                local = f"{conn.laddr[0]}:{conn.laddr[1]}" if conn.laddr else "N/A"
                remote = f"{conn.raddr[0]}:{conn.raddr[1]}" if conn.raddr else "N/A"
                status = conn.status

                self.conn_tree.insert('', 'end', values=(local, remote, status))
                status_counts[status] = status_counts.get(status, 0) + 1

                if conn.raddr:
                    # Plot remote connection on world map (if the remote address is valid)
                    lat, lon = self.get_ip_location(conn.raddr[0])
                    if lat and lon:
                        x, y = self.world_map(lon, lat)
                        self.world_map_ax.plot(x, y, 'ro', markersize=5)

            # Update pie chart for connection statuses
            self.conn_ax.clear()
            self.conn_ax.pie(status_counts.values(), labels=status_counts.keys(), autopct='%1.1f%%', startangle=140)
            self.conn_ax.set_title("Connection Status Distribution")
            self.conn_canvas.draw()

            # Redraw the world map
            self.world_map_canvas.draw()

        except Exception as e:
            print(f"Error updating connections chart: {e}")

    def get_ip_location(self, ip):
        """ Get the latitude and longitude for a given IP using ipinfo.io """
        if ip == '127.0.0.1':  # Skip local IP
            return None, None
        if ip in self.ip_cache:
            return self.ip_cache[ip]

        try:
            # Use ipinfo.io for IP geolocation
            response = requests.get(f"https://ipinfo.io/{ip}/json")
            data = response.json()
            location = data.get('loc', None)
            if location:
                lat, lon = map(float, location.split(','))
                self.ip_cache[ip] = (lat, lon)
                return lat, lon
        except Exception as e:
            print(f"Error getting location for IP {ip}: {e}")
        return None, None

    def update_data(self):
        try:
            # Update all visualizations
            self.update_interface_chart()
            self.update_connections_chart()

            # Schedule next update
            self.root.after(5000, self.update_data)
        except Exception as e:
            print(f"Error in update_data: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkNavigator(root)
    root.mainloop()
